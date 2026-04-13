"""Device 模块 schemas — 产品、设备、分组、影子、指令、固件、OTA。

字段定义必须与 docs/contracts/models/02_device.sql 保持一致。
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import IntEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .common import (
    CommonStatus,
    PageRequest,
    TenantTimestampFields,
)


# ============================================================
# Product
# ============================================================
class ProductAuthType(IntEnum):
    PRODUCT_SECRET = 1   # 一型一密
    DEVICE_SECRET = 2    # 一机一密


class ProductDataFormat(str):
    JSON = "json"
    BINARY = "binary"


class ProductMetricDef(BaseModel):
    """指标定义。"""

    key: str = Field(..., min_length=1, max_length=64)
    name: str = Field(..., min_length=1, max_length=100)
    data_type: str = Field(..., pattern="^(int|float|bool|string|enum|struct)$")
    unit: str | None = None
    min_value: float | None = None
    max_value: float | None = None
    enum_values: list[str] | None = None
    description: str | None = None


class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=2, max_length=50, pattern="^[a-zA-Z0-9_-]+$")
    category: str | None = Field(default=None, max_length=50)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    description: str | None = None
    auth_type: ProductAuthType = ProductAuthType.DEVICE_SECRET
    data_format: str = Field(default="json", pattern="^(json|binary)$")
    metric_schema: list[ProductMetricDef] = Field(default_factory=list)


class ProductCreateRequest(ProductBase):
    pass


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    description: str | None = None
    data_format: str | None = Field(default=None, pattern="^(json|binary)$")
    metric_schema: list[ProductMetricDef] | None = None
    status: CommonStatus | None = None


class ProductResponse(TenantTimestampFields):
    name: str
    code: str
    category: str | None
    manufacturer: str | None
    model: str | None
    description: str | None
    auth_type: int
    data_format: str
    metric_schema: list[ProductMetricDef] = Field(default_factory=list)
    status: int


class ProductPageRequest(PageRequest):
    name: str | None = None
    code: str | None = None
    category: str | None = None
    status: CommonStatus | None = None


# ============================================================
# Device
# ============================================================
class DeviceStatus(IntEnum):
    INACTIVE = 0   # 未激活
    ONLINE = 1
    OFFLINE = 2
    ABNORMAL = 3
    DISABLED = 4


class DeviceLocation(BaseModel):
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    address: str | None = Field(default=None, max_length=200)


class DeviceBase(BaseModel):
    product_id: int | None = None
    device_key: str = Field(..., min_length=4, max_length=100, pattern="^[a-zA-Z0-9_.:-]+$")
    name: str | None = Field(default=None, max_length=100)
    sn: str | None = Field(default=None, max_length=100)
    firmware_version: str | None = Field(default=None, max_length=50)
    hardware_version: str | None = Field(default=None, max_length=50)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    address: str | None = Field(default=None, max_length=200)
    tags: dict[str, Any] = Field(default_factory=dict)
    ext_config: dict[str, Any] = Field(default_factory=dict)
    description: str | None = None


class DeviceCreateRequest(DeviceBase):
    """创建设备时若 auth_type=2(一机一密)，由服务端生成 device_secret。"""

    device_secret: str | None = Field(default=None, min_length=8, max_length=200)
    group_ids: list[int] = Field(default_factory=list)


class DeviceUpdateRequest(BaseModel):
    name: str | None = None
    sn: str | None = None
    firmware_version: str | None = None
    hardware_version: str | None = None
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    address: str | None = None
    tags: dict[str, Any] | None = None
    ext_config: dict[str, Any] | None = None
    description: str | None = None
    status: DeviceStatus | None = None
    group_ids: list[int] | None = None


class DeviceResponse(TenantTimestampFields):
    product_id: int | None
    device_key: str
    name: str | None
    sn: str | None
    firmware_version: str | None
    hardware_version: str | None
    status: int
    activated_at: datetime | None
    last_online_at: datetime | None
    last_offline_at: datetime | None
    last_ip: str | None
    local_ip: str | None
    longitude: Decimal | None
    latitude: Decimal | None
    address: str | None
    tags: dict[str, Any] = Field(default_factory=dict)
    ext_config: dict[str, Any] = Field(default_factory=dict)
    description: str | None
    group_ids: list[int] = Field(default_factory=list)


class DeviceCreateResponse(DeviceResponse):
    """创建一机一密设备时唯一一次返回 device_secret 明文。"""

    device_secret: str | None = None


class DevicePageRequest(PageRequest):
    name: str | None = None
    device_key: str | None = None
    sn: str | None = None
    product_id: int | None = None
    group_id: int | None = None
    status: DeviceStatus | None = None
    last_online_start: datetime | None = None
    last_online_end: datetime | None = None


class DeviceBatchOperationRequest(BaseModel):
    device_ids: list[int] = Field(..., min_length=1, max_length=1000)


class DeviceResetSecretResponse(BaseModel):
    device_id: int
    device_secret: str


# ============================================================
# Device Group
# ============================================================
class DeviceGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    parent_id: int = Field(default=0, ge=0)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = None
    sort: int = 0


class DeviceGroupCreateRequest(DeviceGroupBase):
    pass


class DeviceGroupUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    parent_id: int | None = Field(default=None, ge=0)
    code: str | None = None
    description: str | None = None
    sort: int | None = None


class DeviceGroupResponse(TenantTimestampFields):
    name: str
    parent_id: int
    code: str | None
    description: str | None
    sort: int
    device_count: int = 0


class DeviceGroupTreeResponse(DeviceGroupResponse):
    children: list["DeviceGroupTreeResponse"] = Field(default_factory=list)


class DeviceGroupBindRequest(BaseModel):
    group_id: int = Field(..., gt=0)
    device_ids: list[int] = Field(..., min_length=1, max_length=1000)


# ============================================================
# Device Shadow
# ============================================================
class DeviceShadowResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: int
    tenant_id: int
    reported_state: dict[str, Any] = Field(default_factory=dict)
    desired_state: dict[str, Any] = Field(default_factory=dict)
    reported_at: datetime | None
    desired_at: datetime | None
    version: int
    updated_at: datetime


class DeviceShadowDesiredRequest(BaseModel):
    """下发期望态。"""

    desired_state: dict[str, Any] = Field(..., min_length=1)
    version: int | None = Field(default=None, description="可选：乐观锁版本")


# ============================================================
# Device Command
# ============================================================
class DeviceCommandStatus(IntEnum):
    SENT = 0
    DELIVERED = 1
    EXECUTED = 2
    TIMEOUT = 3
    FAILED = 4


class DeviceCommandRequest(BaseModel):
    command: str = Field(..., min_length=1, max_length=100)
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=30, ge=1, le=600)


class DeviceCommandResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    device_id: int
    command_id: str
    command: str
    params: dict[str, Any]
    status: int
    response: dict[str, Any] | None
    error_message: str | None
    timeout_seconds: int
    sent_at: datetime
    delivered_at: datetime | None
    acked_at: datetime | None
    creator_id: int | None


class DeviceCommandPageRequest(PageRequest):
    device_id: int | None = None
    command: str | None = None
    status: DeviceCommandStatus | None = None
    sent_start: datetime | None = None
    sent_end: datetime | None = None


# ============================================================
# Device Online Log
# ============================================================
class DeviceOnlineEventType(IntEnum):
    ONLINE = 1
    OFFLINE = 2


class DeviceOnlineLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    device_id: int
    event_type: int
    ip: str | None
    reason: str | None
    occurred_at: datetime


class DeviceOnlineLogPageRequest(PageRequest):
    device_id: int | None = None
    event_type: DeviceOnlineEventType | None = None
    occur_start: datetime | None = None
    occur_end: datetime | None = None


# ============================================================
# Firmware Package
# ============================================================
class FirmwareStatus(IntEnum):
    DRAFT = 0
    PUBLISHED = 1
    DEPRECATED = 2


class FirmwarePackageBase(BaseModel):
    product_id: int | None = None
    version: str = Field(..., min_length=1, max_length=50, pattern="^[a-zA-Z0-9._+-]+$")
    name: str = Field(..., min_length=1, max_length=200)
    changelog: str | None = None
    sign_method: str | None = Field(default=None, max_length=20)
    signature: str | None = Field(default=None, max_length=500)


class FirmwarePackageCreateRequest(FirmwarePackageBase):
    """文件需先调用上传接口取得 file_key/file_url/file_size/file_hash。"""

    file_url: str = Field(..., max_length=500)
    file_key: str = Field(..., max_length=500)
    file_size: int = Field(..., ge=1)
    file_hash: str = Field(..., min_length=32, max_length=128)


class FirmwarePackageUpdateRequest(BaseModel):
    name: str | None = None
    changelog: str | None = None
    sign_method: str | None = None
    signature: str | None = None
    status: FirmwareStatus | None = None


class FirmwarePackageResponse(TenantTimestampFields):
    product_id: int | None
    version: str
    name: str
    file_url: str
    file_key: str
    file_size: int
    file_hash: str
    sign_method: str | None
    signature: str | None
    changelog: str | None
    status: int


class FirmwarePackagePageRequest(PageRequest):
    product_id: int | None = None
    version: str | None = None
    name: str | None = None
    status: FirmwareStatus | None = None


# ============================================================
# OTA Job
# ============================================================
class OtaStrategy(IntEnum):
    ALL = 0           # 全量
    PERCENTAGE = 1    # 按比例灰度
    SPECIFIED = 2     # 指定设备


class OtaJobStatus(IntEnum):
    PENDING = 0
    RUNNING = 1
    PAUSED = 2
    COMPLETED = 3
    CANCELED = 4


class OtaStrategyConfig(BaseModel):
    percentage: int | None = Field(default=None, ge=1, le=100)
    device_ids: list[int] | None = None
    product_ids: list[int] | None = None
    group_ids: list[int] | None = None


class OtaJobCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    firmware_id: int = Field(..., gt=0)
    strategy: OtaStrategy = OtaStrategy.ALL
    strategy_config: OtaStrategyConfig = Field(default_factory=OtaStrategyConfig)


class OtaJobResponse(TenantTimestampFields):
    name: str
    firmware_id: int
    strategy: int
    strategy_config: dict[str, Any]
    target_count: int
    pending_count: int
    success_count: int
    failure_count: int
    status: int
    started_at: datetime | None
    completed_at: datetime | None


class OtaJobPageRequest(PageRequest):
    name: str | None = None
    firmware_id: int | None = None
    status: OtaJobStatus | None = None


# ============================================================
# OTA Job Device
# ============================================================
class OtaJobDeviceStatus(IntEnum):
    PENDING_PUSH = 0
    PUSHED = 1
    DOWNLOADING = 2
    UPGRADING = 3
    SUCCESS = 4
    FAILED = 5


class OtaJobDeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tenant_id: int
    job_id: int
    device_id: int
    status: int
    progress: int
    error_message: str | None
    pushed_at: datetime | None
    completed_at: datetime | None


class OtaJobDevicePageRequest(PageRequest):
    job_id: int = Field(..., gt=0)
    device_id: int | None = None
    status: OtaJobDeviceStatus | None = None
