"""SQLAlchemy ``do_orm_execute`` listener that enforces tenant isolation.

The listener inspects each ORM statement; when it targets a
:class:`TenantModel` subclass it injects
``with_loader_criteria(TenantModel, lambda cls: cls.tenant_id == tid)`` so that
every SELECT / UPDATE / DELETE is scoped to the current tenant.

Design notes
------------
* SQLAlchemy's lambda-SQL subsystem forbids calling arbitrary Python functions
  inside the criteria lambda (it must be cacheable), so ``tenant_id`` is read
  from :class:`TenantContext` **before** constructing the lambda and is
  captured as a plain closure variable.
* The decision whether the query touches a tenant entity is made via
  ``ORMExecuteState.all_mappers``.  Plain :class:`BaseModel` queries pass
  through untouched and never raise.
* The listener is installed exactly once (module-level guard) so tests and
  application startup can call :func:`install_tenant_filter` freely.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import event
from sqlalchemy.orm import Session, with_loader_criteria

from app.core.db.tenant_model import TenantModel

from .context import TenantContext, TenantRequiredError, is_tenant_ignored

_LISTENER_INSTALLED: bool = False


def install_tenant_filter() -> None:
    """Register the ``do_orm_execute`` listener exactly once."""
    global _LISTENER_INSTALLED
    if _LISTENER_INSTALLED:
        return
    event.listen(Session, "do_orm_execute", _inject_tenant_filter)
    _LISTENER_INSTALLED = True


def _targets_tenant_model(execute_state: Any) -> bool:
    """Return True if the ORM statement references any TenantModel subclass."""
    try:
        mappers = execute_state.all_mappers
    except AttributeError:
        return False
    for mapper in mappers:
        cls = getattr(mapper, "class_", None)
        if cls is not None and issubclass(cls, TenantModel):
            return True
    return False


def _inject_tenant_filter(execute_state: Any) -> None:
    # INSERTs are never filtered — the caller must supply tenant_id, and the
    # NOT NULL constraint on the column is the backstop.
    if execute_state.is_insert:
        return

    # Explicit escape hatches.
    if execute_state.execution_options.get("tenant_ignore", False):
        return
    if is_tenant_ignored():
        return

    if not _targets_tenant_model(execute_state):
        return

    tid = TenantContext.get()
    if tid is None:
        raise TenantRequiredError(
            "Query against a TenantModel requires tenant_id in context"
        )

    # ``tid`` is captured as a plain int closure variable — SQLAlchemy's
    # lambda-SQL system is happy to bind it as a parameter.
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            TenantModel,
            lambda cls: cls.tenant_id == tid,
            include_aliases=True,
        )
    )
