"""Protocol backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any

from zephyr_re.ble.client import BleClient


class FanSpeed(str, Enum):
    OFF = "off"
    LOW = "low"
    HIGH = "high"


class CommandStatus(str, Enum):
    OK = "ok"
    NOT_IMPLEMENTED = "not_implemented"
    NOT_CONFIGURED = "not_configured"
    ERROR = "error"
    PARTIAL = "partial"


@dataclass
class BatteryInfo:
    percent: int | None
    raw: bytes | None = None
    message: str | None = None


@dataclass
class ColorInfo:
    r: int
    g: int
    b: int
    raw: bytes | None = None


@dataclass
class CommandResult:
    status: CommandStatus
    message: str
    responses: list[bytes] | None = None

    @property
    def ok(self) -> bool:
        """Device acknowledged the command (not merely that bytes were sent)."""
        return self.status == CommandStatus.OK

    @property
    def sent(self) -> bool:
        """Bytes were written to the peripheral."""
        return self.status in (CommandStatus.OK, CommandStatus.PARTIAL)


class ProtocolBackend(ABC):
    """Abstract protocol adapter — implement when wire format is known."""

    name: str = "base"

    @abstractmethod
    async def on_connect(self, client: BleClient) -> None:
        """Called after BLE connect; enable notifications, probe services, etc."""

    @abstractmethod
    async def read_battery(self) -> BatteryInfo | None:
        ...

    @abstractmethod
    async def read_external_color(self) -> ColorInfo | None:
        ...

    @abstractmethod
    async def read_external_brightness(self) -> int | None:
        ...

    @abstractmethod
    async def read_external_effect(self) -> str | None:
        ...

    @abstractmethod
    async def set_external_color(self, r: int, g: int, b: int) -> CommandResult:
        ...

    @abstractmethod
    async def set_external_brightness(self, brightness: int) -> CommandResult:
        ...

    @abstractmethod
    async def set_external_effect(self, effect: str, **opts: Any) -> CommandResult:
        ...

    @abstractmethod
    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0) -> CommandResult:
        ...

    @abstractmethod
    async def set_internal_brightness(self, brightness: int) -> CommandResult:
        ...

    @abstractmethod
    async def set_internal_effect(self, effect: str, **opts: Any) -> CommandResult:
        ...

    @abstractmethod
    async def set_fan_speed(self, speed: FanSpeed) -> CommandResult:
        ...

    @abstractmethod
    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None) -> CommandResult:
        ...
