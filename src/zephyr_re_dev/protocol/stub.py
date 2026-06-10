"""Stub protocol backend — logs intended commands without sending."""

from __future__ import annotations

from typing import Any

from zephyr_re.ble.client import BleClient
from zephyr_re.protocol.base import (
    BatteryInfo,
    ColorInfo,
    CommandResult,
    CommandStatus,
    FanSpeed,
    ProtocolBackend,
)


class StubBackend(ProtocolBackend):
    name = "stub"

    def __init__(self) -> None:
        self._client: BleClient | None = None

    async def on_connect(self, client: BleClient) -> None:
        self._client = client
        client.capture.log("info", message="[STUB] Protocol backend active — commands are logged only")

    async def read_battery(self) -> BatteryInfo | None:
        return BatteryInfo(percent=None, message="[STUB] would read battery")

    async def read_external_color(self) -> ColorInfo | None:
        return None

    async def read_external_brightness(self) -> int | None:
        return None

    async def read_external_effect(self) -> str | None:
        return None

    async def set_external_color(self, r: int, g: int, b: int) -> CommandResult:
        msg = f"[STUB] would set external RGB to #{r:02X}{g:02X}{b:02X}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_external_brightness(self, brightness: int) -> CommandResult:
        msg = f"[STUB] would set external brightness to {brightness}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_external_effect(self, effect: str, **opts: Any) -> CommandResult:
        msg = f"[STUB] would set external effect to {effect!r} opts={opts}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0) -> CommandResult:
        state = "on" if on else "off"
        msg = f"[STUB] would set internal light {state} RGB({r},{g},{b})"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_internal_brightness(self, brightness: int) -> CommandResult:
        msg = f"[STUB] would set internal brightness to {brightness}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_internal_effect(self, effect: str, **opts: Any) -> CommandResult:
        msg = f"[STUB] would set internal effect to {effect!r} opts={opts}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def set_fan_speed(self, speed: FanSpeed) -> CommandResult:
        msg = f"[STUB] would set fan speed to {speed.value}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)

    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None) -> CommandResult:
        msg = f"[STUB] would raw write to {char_uuid or 'default'}: {write_hex}"
        if self._client:
            self._client.capture.log("info", message=msg)
        return CommandResult(CommandStatus.NOT_IMPLEMENTED, msg)
