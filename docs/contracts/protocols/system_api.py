"""System 模块对外暴露的 Protocol 接口。

其它模块（device/weighbridge/...）通过依赖注入获取这些 Provider，
避免直接 import system 模块的具体实现，从而：
1) 解耦模块边界，便于独立测试与替换；
2) 任务编排时可以单独 mock 这些 Provider；
3) 防止跨模块循环依赖。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schemas.system import LoginUserInfo


@runtime_checkable
class TenantProvider(Protocol):
    """租户上下文提供者。"""

    async def get_current_tenant_id(self) -> int:
        """获取当前请求上下文中的 tenant_id。未设置时抛出异常。"""
        ...

    async def is_tenant_active(self, tenant_id: int) -> bool:
        """租户是否处于正常状态（未禁用、未过期）。"""
        ...

    async def get_tenant_quota(self, tenant_id: int) -> "TenantQuota":
        """获取租户配额信息。"""
        ...


class TenantQuota(Protocol):
    device_quota: int
    user_quota: int
    storage_quota: int
    storage_used: int


@runtime_checkable
class UserInfoProvider(Protocol):
    """当前登录用户信息提供者。"""

    async def get_current_user(self) -> LoginUserInfo:
        """获取当前登录用户。未登录时抛出 AuthException。"""
        ...

    async def get_user_by_id(self, user_id: int) -> LoginUserInfo | None:
        """根据 user_id 加载用户（含权限）。"""
        ...

    async def has_permission(self, permission: str) -> bool:
        """当前用户是否拥有指定权限标识。"""
        ...

    async def has_any_permission(self, permissions: list[str]) -> bool:
        ...

    async def has_all_permissions(self, permissions: list[str]) -> bool:
        ...


@runtime_checkable
class DataPermissionProvider(Protocol):
    """数据权限过滤器。

    业务模块在构造查询时调用，注入 dept 范围过滤条件。
    """

    async def get_visible_dept_ids(self, user: LoginUserInfo) -> list[int] | None:
        """返回当前用户可见的部门 id 列表。

        - None 代表全部可见（DataScope.ALL）
        - [] 代表仅本人（SELF_ONLY）— 调用方应改用 user_id 过滤
        - 否则返回部门 id 集合
        """
        ...


@runtime_checkable
class AuditLogger(Protocol):
    """审计日志写入接口。"""

    async def log(
        self,
        *,
        module: str,
        operation: str,
        request_url: str | None = None,
        request_params: dict | None = None,
        response_code: int | None = None,
        duration_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        ...


@runtime_checkable
class EventPublisher(Protocol):
    """事件总线发布接口（Redis Streams）。事件名取自 contracts/events.yaml。"""

    async def publish(self, event: str, payload: dict) -> str:
        """发布事件，返回事件 id。"""
        ...
