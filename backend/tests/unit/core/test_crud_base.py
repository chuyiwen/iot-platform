"""Unit tests for CRUDBase using an in-memory SQLite database (aiosqlite).

No PostgreSQL connection is required.
"""

import pytest
from pydantic import BaseModel as PydanticBase
from sqlalchemy import Integer, String
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base_model import Base, BaseModel
from app.core.db.crud_base import CRUDBase

# ---------------------------------------------------------------------------
# In-process test model
# ---------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class TestItem(BaseModel):
    __tablename__ = "test_items"

    # SQLite does not support BigInteger autoincrement — override with Integer.
    # Production code targets PostgreSQL (BIGSERIAL) and is unaffected.
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    value: Mapped[int] = mapped_column(Integer, default=0)


# ---------------------------------------------------------------------------
# Pydantic schemas for create / update
# ---------------------------------------------------------------------------


class TestItemCreate(PydanticBase):
    name: str
    value: int = 0


class TestItemUpdate(PydanticBase):
    name: str | None = None
    value: int | None = None


# ---------------------------------------------------------------------------
# CRUD instance
# ---------------------------------------------------------------------------

crud = CRUDBase[TestItem, TestItemCreate, TestItemUpdate](TestItem)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncSession:  # type: ignore[misc]
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with async_session() as session:
        yield session
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


async def _create_item(
    db: AsyncSession,
    name: str = "item",
    value: int = 0,
    creator_id: int | None = None,
) -> TestItem:
    obj = await crud.create(db, obj_in=TestItemCreate(name=name, value=value), creator_id=creator_id)
    await db.commit()
    return obj


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create(db: AsyncSession) -> None:
    item = await _create_item(db, name="alpha", value=42, creator_id=1)
    assert item.id is not None
    assert item.id > 0
    assert item.name == "alpha"
    assert item.value == 42
    assert item.creator_id == 1
    assert item.updater_id == 1
    assert item.deleted is False


@pytest.mark.asyncio
async def test_get(db: AsyncSession) -> None:
    item = await _create_item(db, name="beta", value=10, creator_id=2)
    fetched = await crud.get(db, item.id)
    assert fetched is not None
    assert fetched.id == item.id
    assert fetched.name == "beta"
    assert fetched.value == 10


@pytest.mark.asyncio
async def test_get_not_found(db: AsyncSession) -> None:
    result = await crud.get(db, 999999)
    assert result is None


@pytest.mark.asyncio
async def test_get_multi_empty(db: AsyncSession) -> None:
    items, total = await crud.get_multi(db)
    assert items == []
    assert total == 0


@pytest.mark.asyncio
async def test_get_multi_with_data(db: AsyncSession) -> None:
    for i in range(3):
        await _create_item(db, name=f"item_{i}", value=i)

    # fetch first 2 (order by id desc → item_2, item_1)
    items, total = await crud.get_multi(db, skip=0, limit=2, order_by="id", order_desc=True)
    assert total == 3
    assert len(items) == 2


@pytest.mark.asyncio
async def test_get_multi_filters(db: AsyncSession) -> None:
    await _create_item(db, name="foo", value=100)
    await _create_item(db, name="bar", value=200)
    await _create_item(db, name="foo", value=300)

    items, total = await crud.get_multi(db, filters={"name": "foo"})
    assert total == 2
    assert all(it.name == "foo" for it in items)


@pytest.mark.asyncio
async def test_update(db: AsyncSession) -> None:
    item = await _create_item(db, name="original", value=1, creator_id=1)

    updated = await crud.update(
        db,
        db_obj=item,
        obj_in=TestItemUpdate(name="modified", value=99),
        updater_id=7,
    )
    await db.commit()

    assert updated.name == "modified"
    assert updated.value == 99
    assert updated.updater_id == 7
    # creator_id should be unchanged
    assert updated.creator_id == 1


@pytest.mark.asyncio
async def test_soft_delete(db: AsyncSession) -> None:
    item = await _create_item(db, name="to_delete")
    item_id = item.id

    deleted = await crud.soft_delete(db, id=item_id, updater_id=5)
    await db.commit()

    assert deleted is True
    # get() should return None for a soft-deleted record
    assert await crud.get(db, item_id) is None

    # Verify the row still exists in the DB with deleted=True
    from sqlalchemy import select

    result = await db.execute(select(TestItem).where(TestItem.id == item_id))
    row = result.scalars().first()
    assert row is not None
    assert row.deleted is True
    assert row.updater_id == 5


@pytest.mark.asyncio
async def test_soft_delete_not_found(db: AsyncSession) -> None:
    result = await crud.soft_delete(db, id=999999)
    assert result is False
