"""Multi-tenant framework.

Importing this package is enough to activate the SQLAlchemy tenant filter —
:func:`install_tenant_filter` is called on first import and is idempotent.
"""

from .context import TenantContext, TenantRequiredError
from .decorators import tenant_ignore, tenant_ignore_scope
from .deps import get_tenant_id, get_tenant_id_optional
from .filters import install_tenant_filter
from .middleware import TenantMiddleware

# Side-effect: register the do_orm_execute listener.  Idempotent.
install_tenant_filter()

__all__ = [
    "TenantContext",
    "TenantMiddleware",
    "TenantRequiredError",
    "get_tenant_id",
    "get_tenant_id_optional",
    "install_tenant_filter",
    "tenant_ignore",
    "tenant_ignore_scope",
]
