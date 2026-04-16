"""``@tenant_ignore`` decorator and ``tenant_ignore_scope`` context manager.

Both lift the automatic tenant filter for the duration of the wrapped call.
Use sparingly — mostly for cross-tenant platform/admin operations and for
background tasks that legitimately need to iterate over all tenants.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import TypeVar, cast

from .context import _pop_tenant_ignore, _push_tenant_ignore

F = TypeVar("F", bound=Callable[..., object])


def tenant_ignore(func: F) -> F:
    """Decorator that disables the tenant filter inside *func*.

    Works on both sync and async callables.  Nesting is safe — the flag is
    restored to its previous value when the wrapped call returns.
    """

    if inspect.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: object, **kwargs: object) -> object:
            token = _push_tenant_ignore()
            try:
                return await func(*args, **kwargs)  # type: ignore[misc]
            finally:
                _pop_tenant_ignore(token)

        return cast(F, async_wrapper)

    @functools.wraps(func)
    def sync_wrapper(*args: object, **kwargs: object) -> object:
        token = _push_tenant_ignore()
        try:
            return func(*args, **kwargs)
        finally:
            _pop_tenant_ignore(token)

    return cast(F, sync_wrapper)


@contextmanager
def tenant_ignore_scope() -> Iterator[None]:
    """Context-manager form of :func:`tenant_ignore` for inline use."""
    token = _push_tenant_ignore()
    try:
        yield
    finally:
        _pop_tenant_ignore(token)
