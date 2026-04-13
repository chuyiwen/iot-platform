"""System 模块 schemas — 租户、用户、角色、菜单、部门、API Key、审计日志、OAuth2。

字段定义必须与 docs/contracts/models/01_system.sql 保持一致。
"""
from __future__ import annotations

from datetime import datetime
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .common import (
    CommonStatus,
    DataScope,
    PageRequest,
    TenantTimestampFields,
    TimestampFields,
)


# ============================================================
# Tenant
# ============================================================
class TenantStatus(IntEnum):
    NORMAL = 0
    DISABLED = 1


class TenantBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-z0-9_-]+$")
    domain: str | None = Field(default=None, max_length=200)
    contact_name: str | None = Field(default=None, max_length=50)
    contact_phone: str | None = Field(default=None, max_length=20)
    contact_email: EmailStr | None = None
    package_id: int | None = None
    expire_at: datetime | None = None
    device_quota: int = Field(default=100, ge=0)
    user_quota: int = Field(default=50, ge=0)
    storage_quota: int = Field(default=10737418240, ge=0)
    remark: str | None = None


class TenantCreateRequest(TenantBase):
    """创建租户时同时创建超级管理员账号。"""

    admin_username: str = Field(..., min_length=3, max_length=50)
    admin_password: str = Field(..., min_length=8, max_length=64)
    admin_nickname: str | None = None


class TenantUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    domain: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: EmailStr | None = None
    expire_at: datetime | None = None
    device_quota: int | None = Field(default=None, ge=0)
    user_quota: int | None = Field(default=None, ge=0)
    storage_quota: int | None = Field(default=None, ge=0)
    status: TenantStatus | None = None
    remark: str | None = None


class TenantResponse(TimestampFields):
    name: str
    code: str
    domain: str | None
    contact_name: str | None
    contact_phone: str | None
    contact_email: str | None
    package_id: int | None
    status: int
    expire_at: datetime | None
    device_quota: int
    user_quota: int
    storage_quota: int
    storage_used: int
    remark: str | None


class TenantPageRequest(PageRequest):
    name: str | None = None
    code: str | None = None
    status: TenantStatus | None = None


# ============================================================
# Department
# ============================================================
class DeptBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int = Field(default=0, ge=0)
    sort: int = 0
    leader_id: int | None = None
    phone: str | None = None
    email: EmailStr | None = None


class DeptCreateRequest(DeptBase):
    pass


class DeptUpdateRequest(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    sort: int | None = None
    leader_id: int | None = None
    phone: str | None = None
    email: EmailStr | None = None
    status: CommonStatus | None = None


class DeptResponse(TenantTimestampFields):
    name: str
    parent_id: int
    sort: int
    leader_id: int | None
    phone: str | None
    email: str | None
    status: int


class DeptTreeResponse(DeptResponse):
    children: list["DeptTreeResponse"] = Field(default_factory=list)


# ============================================================
# User
# ============================================================
class UserSex(IntEnum):
    UNKNOWN = 0
    MALE = 1
    FEMALE = 2


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    nickname: str | None = Field(default=None, max_length=50)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=20)
    avatar: str | None = Field(default=None, max_length=500)
    dept_id: int | None = None
    sex: UserSex | None = None
    remark: str | None = None


class UserCreateRequest(UserBase):
    password: str = Field(..., min_length=8, max_length=64)
    role_ids: list[int] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    nickname: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    avatar: str | None = None
    dept_id: int | None = None
    sex: UserSex | None = None
    status: CommonStatus | None = None
    role_ids: list[int] | None = None
    remark: str | None = None


class UserResetPasswordRequest(BaseModel):
    password: str = Field(..., min_length=8, max_length=64)


class UserChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=64)


class UserResponse(TenantTimestampFields):
    username: str
    nickname: str | None
    email: str | None
    phone: str | None
    avatar: str | None
    dept_id: int | None
    sex: int | None
    status: int
    is_super: bool
    last_login_at: datetime | None
    last_login_ip: str | None
    remark: str | None
    role_ids: list[int] = Field(default_factory=list)


class UserPageRequest(PageRequest):
    username: str | None = None
    nickname: str | None = None
    phone: str | None = None
    dept_id: int | None = None
    status: CommonStatus | None = None
    create_start: datetime | None = None
    create_end: datetime | None = None


class LoginUserInfo(BaseModel):
    """认证后的当前用户信息（存于 Redis）。"""

    model_config = ConfigDict(from_attributes=True)

    user_id: int
    tenant_id: int
    username: str
    nickname: str | None = None
    is_super: bool = False
    dept_id: int | None = None
    role_ids: list[int] = Field(default_factory=list)
    role_codes: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
    data_scope: DataScope = DataScope.SELF_ONLY
    data_scope_dept_ids: list[int] = Field(default_factory=list)


# ============================================================
# Role
# ============================================================
class RoleType(IntEnum):
    SYSTEM = 1   # 内置不可删
    CUSTOM = 2


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    sort: int = 0
    data_scope: DataScope = DataScope.SELF_ONLY
    data_scope_dept_ids: list[int] = Field(default_factory=list)
    remark: str | None = None


class RoleCreateRequest(RoleBase):
    menu_ids: list[int] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: str | None = None
    sort: int | None = None
    data_scope: DataScope | None = None
    data_scope_dept_ids: list[int] | None = None
    status: CommonStatus | None = None
    menu_ids: list[int] | None = None
    remark: str | None = None


class RoleResponse(TenantTimestampFields):
    name: str
    code: str
    sort: int
    data_scope: int
    data_scope_dept_ids: list[int]
    status: int
    type: int
    remark: str | None
    menu_ids: list[int] = Field(default_factory=list)


class RolePageRequest(PageRequest):
    name: str | None = None
    code: str | None = None
    status: CommonStatus | None = None


# ============================================================
# Menu
# ============================================================
class MenuType(IntEnum):
    DIRECTORY = 1
    MENU = 2
    BUTTON = 3


class MenuBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)
    parent_id: int = Field(default=0, ge=0)
    permission: str | None = Field(default=None, max_length=100)
    type: MenuType
    sort: int = 0
    path: str | None = None
    icon: str | None = None
    component: str | None = None
    component_name: str | None = None
    visible: bool = True
    keep_alive: bool = True
    always_show: bool = False


class MenuCreateRequest(MenuBase):
    pass


class MenuUpdateRequest(BaseModel):
    name: str | None = None
    parent_id: int | None = None
    permission: str | None = None
    sort: int | None = None
    path: str | None = None
    icon: str | None = None
    component: str | None = None
    component_name: str | None = None
    visible: bool | None = None
    keep_alive: bool | None = None
    always_show: bool | None = None
    status: CommonStatus | None = None


class MenuResponse(TimestampFields):
    name: str
    parent_id: int
    permission: str | None
    type: int
    sort: int
    path: str | None
    icon: str | None
    component: str | None
    component_name: str | None
    visible: bool
    keep_alive: bool
    always_show: bool
    status: int


class MenuTreeResponse(MenuResponse):
    children: list["MenuTreeResponse"] = Field(default_factory=list)


# ============================================================
# Auth / Login
# ============================================================
class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=64)
    tenant_code: str | None = None
    captcha_id: str | None = None
    captcha_code: str | None = None


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int
    user: LoginUserInfo


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


# ============================================================
# API Key
# ============================================================
class ApiKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    scopes: list[str] = Field(default_factory=list)
    expire_at: datetime | None = None
    remark: str | None = None


class ApiKeyResponse(TenantTimestampFields):
    name: str
    key_prefix: str
    scopes: list[str]
    expire_at: datetime | None
    last_used_at: datetime | None
    last_used_ip: str | None
    status: int
    remark: str | None


class ApiKeyCreateResponse(ApiKeyResponse):
    """创建时唯一一次返回完整 key（之后不再返回）。"""

    full_key: str


# ============================================================
# Audit Log
# ============================================================
class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int | None
    user_id: int | None
    username: str | None
    module: str
    operation: str
    method: str | None
    request_url: str | None
    request_params: dict[str, Any] | None
    response_code: int | None
    ip: str | None
    user_agent: str | None
    duration_ms: int | None
    error_message: str | None
    trace_id: str | None
    created_at: datetime


class AuditLogPageRequest(PageRequest):
    user_id: int | None = None
    username: str | None = None
    module: str | None = None
    operation: str | None = None
    response_code: int | None = None
    create_start: datetime | None = None
    create_end: datetime | None = None


# ============================================================
# OAuth2 Client
# ============================================================
class OAuth2ClientCreateRequest(BaseModel):
    client_id: str = Field(..., min_length=4, max_length=100)
    client_secret: str = Field(..., min_length=8, max_length=200)
    name: str
    description: str | None = None
    redirect_uris: list[str] = Field(default_factory=list)
    grant_types: list[str] = Field(default_factory=lambda: ["password"])
    scopes: list[str] = Field(default_factory=list)
    access_token_validity_seconds: int = 1800
    refresh_token_validity_seconds: int = 2592000


class OAuth2ClientUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    redirect_uris: list[str] | None = None
    grant_types: list[str] | None = None
    scopes: list[str] | None = None
    access_token_validity_seconds: int | None = None
    refresh_token_validity_seconds: int | None = None
    status: CommonStatus | None = None


class OAuth2ClientResponse(TenantTimestampFields):
    client_id: str
    name: str
    description: str | None
    redirect_uris: list[str]
    grant_types: list[str]
    scopes: list[str]
    access_token_validity_seconds: int
    refresh_token_validity_seconds: int
    status: int
