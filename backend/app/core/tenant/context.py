"""Tenant context stored in a ContextVar for per-request isolation.

The context is read by the SQLAlchemy ``do_orm_execute`` listener installed in
``filters.py``.  The listener injects ``WHERE tenant_id = :tid`` on every ORM
query that touches a :class:`TenantModel` subclass.
"""

from __future__ import annotations

from contextvars import ContextVar, Token

# ---------------------------------------------------------------------------
# Private context variables
# ---------------------------------------------------------------------------

_tenant_id: ContextVar[int | None] = ContextVar("iot_tenant_id", default=None)
_tenant_ignore: ContextVar[bool] = ContextVar("iot_tenant_ignore", default=False)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class TenantRequiredError(RuntimeError):
    """Raised when an ORM query touches a TenantModel without tenant_id set.

    This is the last line of defence against accidentally reading or mutating
    cross-tenant data.  In production the middleware binds ``tenant_id`` from
    the request headers before the handler runs; seeing this error usually
    means (a) a missing ``X-Tenant-Id`` header, (b) a background task that
    forgot to copy the context, or (c) an internal call that should be
    wrapped in :func:`tenant_ignore_scope`.
    """


# ---------------------------------------------------------------------------
# Public facade
# ---------------------------------------------------------------------------


class TenantContext:
    """Tiny facade around the private ``_tenant_id`` ContextVar."""

    @staticmethod
    def get() -> int | None:
        return _tenant_id.get()

    @staticmethod
    def set(tenant_id: int) -> Token[int | None]:
        if not isinstance(tenant_id, int) or isinstance(tenant_id, bool):
            raise TypeError(f"tenant_id must be int, got {type(tenant_id).__name__}")
        if tenant_id <= 0:
            raise ValueError(f"tenant_id must be positive, got {tenant_id}")
        return _tenant_id.set(tenant_id)

    @staticmethod
    def reset(token: Token[int | None]) -> None:
        _tenant_id.reset(token)

    @staticmethod
    def clear() -> None:
        _tenant_id.set(None)

    @staticmethod
    def require() -> int:
        tid = _tenant_id.get()
        if tid is None:
            raise TenantRequiredError("tenant_id is not set in the current context")
        return tid


# ---------------------------------------------------------------------------
# tenant_ignore flag — module-internal API consumed by decorators.py / filters.py
# ---------------------------------------------------------------------------


def is_tenant_ignored() -> bool:
    """Return True if the current context is inside a ``tenant_ignore`` scope."""
    return _tenant_ignore.get()


def _push_tenant_ignore() -> Token[bool]:
    return _tenant_ignore.set(True)


def _pop_tenant_ignore(token: Token[bool]) -> None:
    _tenant_ignore.reset(token)
