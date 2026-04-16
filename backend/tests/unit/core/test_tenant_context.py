"""Unit tests for ``app.core.tenant`` — context, isolation, decorators.

These tests do not touch SQLAlchemy.  The full filter is exercised by the
integration test ``tests/integration/test_tenant_isolation.py``.
"""

from __future__ import annotations

import asyncio

import pytest

from app.core.tenant import (
    TenantContext,
    TenantRequiredError,
    tenant_ignore,
    tenant_ignore_scope,
)
from app.core.tenant.context import is_tenant_ignored


# ---------------------------------------------------------------------------
# TenantContext basics
# ---------------------------------------------------------------------------


class TestContextBasics:
    def setup_method(self) -> None:
        TenantContext.clear()

    def test_default_is_none(self) -> None:
        assert TenantContext.get() is None

    def test_set_and_get(self) -> None:
        token = TenantContext.set(42)
        try:
            assert TenantContext.get() == 42
        finally:
            TenantContext.reset(token)
        assert TenantContext.get() is None

    def test_require_returns_value(self) -> None:
        token = TenantContext.set(7)
        try:
            assert TenantContext.require() == 7
        finally:
            TenantContext.reset(token)

    def test_require_raises_when_unset(self) -> None:
        with pytest.raises(TenantRequiredError):
            TenantContext.require()

    def test_nested_set_and_reset(self) -> None:
        t1 = TenantContext.set(1)
        t2 = TenantContext.set(2)
        assert TenantContext.get() == 2
        TenantContext.reset(t2)
        assert TenantContext.get() == 1
        TenantContext.reset(t1)
        assert TenantContext.get() is None

    def test_set_rejects_non_positive(self) -> None:
        with pytest.raises(ValueError):
            TenantContext.set(0)
        with pytest.raises(ValueError):
            TenantContext.set(-5)

    def test_set_rejects_non_int(self) -> None:
        with pytest.raises(TypeError):
            TenantContext.set("1")  # type: ignore[arg-type]

    def test_set_rejects_bool(self) -> None:
        # ``bool`` is a subclass of ``int`` in Python — reject it explicitly so
        # that ``True`` is never silently interpreted as tenant_id=1.
        with pytest.raises(TypeError):
            TenantContext.set(True)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Context isolation across asyncio tasks
# ---------------------------------------------------------------------------


class TestContextIsolation:
    async def test_tasks_are_isolated(self) -> None:
        """Two sibling tasks must never observe each other's tenant_id."""
        TenantContext.clear()
        observed: dict[str, int | None] = {}

        async def worker(name: str, tid: int, hold: float) -> None:
            token = TenantContext.set(tid)
            try:
                await asyncio.sleep(hold)
                observed[name] = TenantContext.get()
            finally:
                TenantContext.reset(token)

        await asyncio.gather(
            worker("a", 1, 0.02),
            worker("b", 2, 0.01),
            worker("c", 3, 0.03),
        )

        assert observed == {"a": 1, "b": 2, "c": 3}
        # Outer context is untouched by any child task.
        assert TenantContext.get() is None

    async def test_child_task_inherits_parent_context(self) -> None:
        """``asyncio.create_task`` copies the parent's context at creation."""
        TenantContext.clear()
        token = TenantContext.set(9)
        try:
            captured: list[int | None] = []

            async def child() -> None:
                captured.append(TenantContext.get())

            await asyncio.create_task(child())
            assert captured == [9]
        finally:
            TenantContext.reset(token)


# ---------------------------------------------------------------------------
# tenant_ignore decorator & scope
# ---------------------------------------------------------------------------


class TestTenantIgnore:
    def test_default_flag_is_false(self) -> None:
        assert is_tenant_ignored() is False

    async def test_decorator_on_async(self) -> None:
        assert is_tenant_ignored() is False

        @tenant_ignore
        async def inner() -> bool:
            return is_tenant_ignored()

        assert await inner() is True
        assert is_tenant_ignored() is False  # restored

    def test_decorator_on_sync(self) -> None:
        assert is_tenant_ignored() is False

        @tenant_ignore
        def inner() -> bool:
            return is_tenant_ignored()

        assert inner() is True
        assert is_tenant_ignored() is False

    def test_decorator_restores_on_exception(self) -> None:
        @tenant_ignore
        def boom() -> None:
            raise RuntimeError("x")

        with pytest.raises(RuntimeError):
            boom()
        assert is_tenant_ignored() is False

    def test_scope_context_manager(self) -> None:
        assert is_tenant_ignored() is False
        with tenant_ignore_scope():
            assert is_tenant_ignored() is True
        assert is_tenant_ignored() is False

    def test_nested_scope(self) -> None:
        with tenant_ignore_scope():
            assert is_tenant_ignored() is True
            with tenant_ignore_scope():
                assert is_tenant_ignored() is True
            assert is_tenant_ignored() is True
        assert is_tenant_ignored() is False
