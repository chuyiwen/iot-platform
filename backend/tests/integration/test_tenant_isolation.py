"""Integration tests for automatic tenant filtering via ``do_orm_execute``.

These tests use SQLite-in-memory and define two throw-away models:

* ``TenantItem``   — inherits from ``TenantModel`` (subject to filtering)
* ``PublicItem``   — inherits from ``BaseModel`` (never filtered)

Seed data: 3 rows for tenant 1, 2 rows for tenant 2, 1 public row.
"""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
from sqlalchemy import Integer, String, delete, select, update
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Mapped, mapped_column

# Importing the package installs the do_orm_execute listener as a side-effect.
from app.core.db.base_model import Base, BaseModel
from app.core.db.tenant_model import TenantModel
from app.core.tenant import (
    TenantContext,
    TenantRequiredError,
    tenant_ignore,
    tenant_ignore_scope,
)


# ---------------------------------------------------------------------------
# Throw-away ORM models used only by this test module
# ---------------------------------------------------------------------------


class TenantItem(TenantModel):
    __tablename__ = "tenant_items"

    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[int] = mapped_column(Integer, default=0)


class PublicItem(BaseModel):
    __tablename__ = "public_items"

    name: Mapped[str] = mapped_column(String(100))


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def seeded(db: AsyncSession) -> AsyncSession:
    # INSERTs via session.add bypass do_orm_execute entirely, so we can seed
    # without setting TenantContext.
    db.add_all(
        [
            TenantItem(tenant_id=1, name="a1", value=10),
            TenantItem(tenant_id=1, name="a2", value=20),
            TenantItem(tenant_id=1, name="a3", value=30),
            TenantItem(tenant_id=2, name="b1", value=100),
            TenantItem(tenant_id=2, name="b2", value=200),
            PublicItem(name="public_row"),
        ]
    )
    await db.commit()
    # Ensure every test starts with a clean context.
    TenantContext.clear()
    return db


# ---------------------------------------------------------------------------
# SELECT filtering
# ---------------------------------------------------------------------------


class TestSelectFiltering:
    async def test_tenant_1_sees_only_its_rows(self, seeded: AsyncSession) -> None:
        token = TenantContext.set(1)
        try:
            result = await seeded.execute(select(TenantItem))
            items = result.scalars().all()
        finally:
            TenantContext.reset(token)

        assert len(items) == 3
        assert {i.name for i in items} == {"a1", "a2", "a3"}
        assert all(i.tenant_id == 1 for i in items)

    async def test_tenant_2_sees_only_its_rows(self, seeded: AsyncSession) -> None:
        token = TenantContext.set(2)
        try:
            result = await seeded.execute(select(TenantItem))
            items = result.scalars().all()
        finally:
            TenantContext.reset(token)

        assert len(items) == 2
        assert {i.name for i in items} == {"b1", "b2"}
        assert all(i.tenant_id == 2 for i in items)

    async def test_other_tenant_rows_invisible_even_with_filter(
        self, seeded: AsyncSession
    ) -> None:
        """Row with value=100 belongs to tenant 2 and must be hidden from tenant 1."""
        token = TenantContext.set(1)
        try:
            result = await seeded.execute(
                select(TenantItem).where(TenantItem.value == 100)
            )
            assert result.scalars().first() is None
        finally:
            TenantContext.reset(token)

    async def test_missing_context_raises_on_tenant_model(
        self, seeded: AsyncSession
    ) -> None:
        with pytest.raises(TenantRequiredError):
            await seeded.execute(select(TenantItem))

    async def test_public_model_works_without_context(
        self, seeded: AsyncSession
    ) -> None:
        result = await seeded.execute(select(PublicItem))
        items = result.scalars().all()
        assert len(items) == 1
        assert items[0].name == "public_row"


# ---------------------------------------------------------------------------
# tenant_ignore escape
# ---------------------------------------------------------------------------


class TestTenantIgnoreEscape:
    async def test_scope_sees_all_rows(self, seeded: AsyncSession) -> None:
        with tenant_ignore_scope():
            result = await seeded.execute(select(TenantItem))
            items = result.scalars().all()
        assert len(items) == 5

    async def test_decorator_sees_all_rows(self, seeded: AsyncSession) -> None:
        @tenant_ignore
        async def fetch_all() -> list[TenantItem]:
            result = await seeded.execute(select(TenantItem))
            return list(result.scalars().all())

        items = await fetch_all()
        assert len(items) == 5

    async def test_execution_option_sees_all_rows(self, seeded: AsyncSession) -> None:
        stmt = select(TenantItem).execution_options(tenant_ignore=True)
        result = await seeded.execute(stmt)
        items = result.scalars().all()
        assert len(items) == 5

    async def test_ignore_flag_restored_after_scope(
        self, seeded: AsyncSession
    ) -> None:
        with tenant_ignore_scope():
            await seeded.execute(select(TenantItem))
        # Back outside the scope — querying without tenant_id must raise again.
        with pytest.raises(TenantRequiredError):
            await seeded.execute(select(TenantItem))


# ---------------------------------------------------------------------------
# UPDATE / DELETE filtering (guarding cross-tenant writes)
# ---------------------------------------------------------------------------


class TestUpdateDeleteFiltering:
    async def test_bulk_update_restricted_to_tenant(
        self, seeded: AsyncSession
    ) -> None:
        """Bulk ORM update from tenant 1 must not touch tenant 2 rows."""
        token = TenantContext.set(1)
        try:
            await seeded.execute(update(TenantItem).values(value=999))
            await seeded.commit()
        finally:
            TenantContext.reset(token)

        with tenant_ignore_scope():
            result = await seeded.execute(select(TenantItem))
            items = {item.name: item.value for item in result.scalars().all()}

        assert items["a1"] == 999
        assert items["a2"] == 999
        assert items["a3"] == 999
        assert items["b1"] == 100  # untouched
        assert items["b2"] == 200  # untouched

    async def test_bulk_delete_restricted_to_tenant(
        self, seeded: AsyncSession
    ) -> None:
        token = TenantContext.set(2)
        try:
            await seeded.execute(delete(TenantItem))
            await seeded.commit()
        finally:
            TenantContext.reset(token)

        with tenant_ignore_scope():
            result = await seeded.execute(select(TenantItem))
            remaining = result.scalars().all()

        # Only tenant 1 rows survived.
        assert len(remaining) == 3
        assert all(item.tenant_id == 1 for item in remaining)

    async def test_bulk_update_requires_tenant(self, seeded: AsyncSession) -> None:
        with pytest.raises(TenantRequiredError):
            await seeded.execute(update(TenantItem).values(value=1))
