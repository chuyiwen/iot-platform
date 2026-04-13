"""Device 模块对外暴露的 Protocol 接口。

供 weighbridge / appointment / dispatch / image / telemetry 等下游模块使用。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..schemas.device import (
    DeviceCommandResponse,
    DeviceResponse,
    DeviceShadowResponse,
)


@runtime_checkable
class DeviceQueryProvider(Protocol):
    """设备查询接口。"""

    async def get_device(self, device_id: int) -> DeviceResponse | None:
        ...

    async def get_device_by_key(self, device_key: str) -> DeviceResponse | None:
        ...

    async def list_devices_by_ids(self, device_ids: list[int]) -> list[DeviceResponse]:
        ...

    async def list_devices_by_group(self, group_id: int) -> list[DeviceResponse]:
        ...

    async def list_devices_by_product(self, product_id: int) -> list[DeviceResponse]:
        ...

    async def is_device_online(self, device_id: int) -> bool:
        ...


@runtime_checkable
class DeviceCommandPublisher(Protocol):
    """设备指令下发接口（异步：写库 + 推 MQTT）。"""

    async def send_command(
        self,
        *,
        device_id: int,
        command: str,
        params: dict,
        timeout_seconds: int = 30,
    ) -> DeviceCommandResponse:
        ...

    async def send_command_batch(
        self,
        *,
        device_ids: list[int],
        command: str,
        params: dict,
        timeout_seconds: int = 30,
    ) -> list[DeviceCommandResponse]:
        ...


@runtime_checkable
class DeviceShadowProvider(Protocol):
    """设备影子读写接口。"""

    async def get_shadow(self, device_id: int) -> DeviceShadowResponse | None:
        ...

    async def update_desired(
        self,
        *,
        device_id: int,
        desired_state: dict,
        version: int | None = None,
    ) -> DeviceShadowResponse:
        ...

    async def update_reported(
        self,
        *,
        device_id: int,
        reported_state: dict,
    ) -> DeviceShadowResponse:
        ...


@runtime_checkable
class DeviceAuthProvider(Protocol):
    """设备认证接口（供 EMQX webhook / MQTT auth plugin 调用）。"""

    async def authenticate(
        self,
        *,
        device_key: str,
        password: str,
        client_id: str | None = None,
    ) -> "DeviceAuthResult":
        ...

    async def authorize_topic(
        self,
        *,
        device_id: int,
        topic: str,
        action: str,
    ) -> bool:
        ...


class DeviceAuthResult(Protocol):
    success: bool
    device_id: int | None
    tenant_id: int | None
    reason: str | None
