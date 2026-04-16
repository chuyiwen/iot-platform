"""FastAPI dependency helpers for reading the current tenant id."""

from __future__ import annotations

from .context import TenantContext


def get_tenant_id() -> int:
    """Return the current tenant_id, raising ``TenantRequiredError`` when unset.

    Use this as a FastAPI ``Depends`` on any endpoint that must be scoped to a
    tenant.  The middleware is responsible for setting the value before the
    handler runs.
    """
    return TenantContext.require()


def get_tenant_id_optional() -> int | None:
    """Return the current tenant_id, or ``None`` when unset.

    Use this for endpoints that are tenant-aware but still callable without a
    tenant (for example platform-level admin endpoints).
    """
    return TenantContext.get()
