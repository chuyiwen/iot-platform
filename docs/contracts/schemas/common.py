"""通用 schemas — 分页、响应、基础类型。

所有 API 响应必须使用 ApiResponse 包装。
所有列表查询必须使用 PageRequest / PageResponse。
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


# ============ 统一响应 ============
class ApiResponse(BaseModel, Generic[T]):
    """统一 API 响应包装。"""

    code: int = Field(default=0, description="错误码，0=成功")
    message: str = Field(default="success", description="错误消息")
    data: T | None = Field(default=None, description="响应数据")
    trace_id: str | None = Field(default=None, description="链路追踪 ID")


# ============ 分页 ============
class PageRequest(BaseModel):
    """分页请求基类。"""

    page: int = Field(default=1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(default=20, ge=1, le=200, description="每页条数")
    sort_by: str | None = Field(default=None, description="排序字段")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$", description="排序方向")


class PageResponse(BaseModel, Generic[T]):
    """分页响应。"""

    items: list[T] = Field(default_factory=list, description="数据列表")
    total: int = Field(default=0, description="总条数")
    page: int = Field(default=1, description="当前页码")
    page_size: int = Field(default=20, description="每页条数")


# ============ 时间范围 ============
class TimeRange(BaseModel):
    """时间范围筛选。"""

    start_time: datetime | None = None
    end_time: datetime | None = None


# ============ 基础 ID 输入 ============
class IdRequest(BaseModel):
    id: int = Field(..., gt=0)


class IdsRequest(BaseModel):
    ids: list[int] = Field(..., min_length=1, max_length=1000)


# ============ 通用枚举 ============
class CommonStatus(IntEnum):
    """通用状态：0 正常 / 1 禁用。"""

    ENABLED = 0
    DISABLED = 1


class DataScope(IntEnum):
    """数据权限范围（与 yudao 一致）。"""

    ALL = 1                  # 全部数据
    DEPT_CUSTOM = 2          # 指定部门
    DEPT_ONLY = 3            # 本部门
    DEPT_AND_CHILD = 4       # 本部门及下级
    SELF_ONLY = 5            # 仅本人


# ============ 基础响应字段 ============
class TimestampFields(BaseModel):
    """所有响应模型继承此基类。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
    creator_id: int | None = None
    updater_id: int | None = None


class TenantTimestampFields(TimestampFields):
    """租户隔离的响应模型基类。"""

    tenant_id: int


# ============ 健康检查 ============
class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "0.1.0"
    timestamp: datetime
    services: dict[str, str] = Field(default_factory=dict)


# ============ 错误响应 ============
class ErrorDetail(BaseModel):
    field: str | None = None
    message: str
    type: str | None = None


class ErrorResponse(BaseModel):
    code: int
    message: str
    details: list[ErrorDetail] | None = None
    trace_id: str | None = None
