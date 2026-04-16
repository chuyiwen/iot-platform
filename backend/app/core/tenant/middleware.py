"""FastAPI / Starlette middleware that binds ``X-Tenant-Id`` to the context.

Public / unauthenticated paths (``/health``, Swagger, OpenAPI, ReDoc) are
allowed through without a tenant.  For every other request the middleware
reads the header, validates it, and installs it into :class:`TenantContext`
for the duration of the handler.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from .context import TenantContext

# Paths (or path prefixes) that bypass tenant extraction entirely.
_IGNORED_EXACT: frozenset[str] = frozenset(
    {
        "/health",
        "/openapi.json",
    }
)
_IGNORED_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
)


def _is_public_path(path: str) -> bool:
    if path in _IGNORED_EXACT:
        return True
    return any(path == p or path.startswith(p + "/") for p in _IGNORED_PREFIXES)


class TenantMiddleware(BaseHTTPMiddleware):
    """Parse ``X-Tenant-Id`` and expose it through :class:`TenantContext`."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Tenant-Id") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if _is_public_path(request.url.path):
            return await call_next(request)

        raw = request.headers.get(self.header_name)
        token = None
        if raw:
            try:
                tid = int(raw)
            except ValueError:
                # Malformed header: leave the context unset so downstream
                # dependencies (``get_tenant_id``) raise a well-formed error.
                tid = 0
            if tid > 0:
                token = TenantContext.set(tid)

        try:
            return await call_next(request)
        finally:
            if token is not None:
                TenantContext.reset(token)
