"""Public Zephyr control API — one method per Hazel app feature."""

from __future__ import annotations

from zephyr_re.ble.connector import ZephyrConnector
from zephyr_re.protocol.base import CommandResult, CommandStatus, FanSpeed
from zephyr_re.constants import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE
from zephyr_re.protocol.packets import (
    WAVE_RATE_FACTORY,
    effect_packets,
    fan_speed_packets,
)
from zephyr_re.util.hexio import format_hex


class Zephyr:
    """Control a Razer Zephyr over BLE.

    Transport is ``ZephyrConnector``; this class only builds packets and maps
    replies to ``CommandResult``. Safe to import from a future GUI app.
    """

    def __init__(self, connector: ZephyrConnector | None = None) -> None:
        self._conn = connector or ZephyrConnector()
        self._req_id = 0x30

    @property
    def connector(self) -> ZephyrConnector:
        return self._conn

    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected

    async def connect(self) -> str:
        """Auto-find and connect. Returns device address."""
        return await self._conn.connect_foolproof()

    async def disconnect(self) -> None:
        await self._conn.disconnect()

    def _next_req_id(self) -> int:
        rid = self._req_id
        self._req_id = (self._req_id + 1) & 0xFF
        return rid

    def _result(self, label: str, frames: list[bytes], *, ack: bool, ok: str) -> CommandResult:
        if ack:
            return CommandResult(CommandStatus.OK, ok, frames)
        if frames:
            sample = "; ".join(format_hex(f) for f in frames[:2])
            return CommandResult(CommandStatus.PARTIAL, f"{label} — unexpected reply: {sample}", frames)
        return CommandResult(
            CommandStatus.PARTIAL,
            f"{label} — sent, no notify ack",
            frames,
        )

    async def _send_pair(self, label: str, header: bytes, payload: bytes) -> CommandResult:
        if not self._conn.vendor_available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor GATT not available")
        exchange = await self._conn.send([header, payload])
        return self._result(label, exchange.frames, ack=exchange.ack, ok=label)

    async def _send_effect(self, zone: int, effect: str, label: str, **opts) -> CommandResult:
        try:
            header, payload = effect_packets(self._next_req_id(), effect, zone, **opts)
        except ValueError as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))
        return await self._send_pair(label, header, payload)

    async def _send_fan(self, speed: FanSpeed, label: str) -> CommandResult:
        header, payload = fan_speed_packets(self._next_req_id(), speed)
        return await self._send_pair(label, header, payload)

    # --- 1. Fan speed ---

    async def fan_low(self) -> CommandResult:
        return await self._send_fan(FanSpeed.LOW, "Fan low")

    async def fan_high(self) -> CommandResult:
        return await self._send_fan(FanSpeed.HIGH, "Fan high")

    async def fan_off(self) -> CommandResult:
        return await self._send_fan(FanSpeed.OFF, "Fan off")

    # --- 2. Internal lighting ---

    async def internal_static(self, r: int, g: int, b: int) -> CommandResult:
        return await self._send_effect(
            INTERNAL_LIGHT_ZONE,
            "static",
            f"Internal static #{r:02X}{g:02X}{b:02X}",
            r=r,
            g=g,
            b=b,
        )

    async def internal_spectrum(self) -> CommandResult:
        return await self._send_effect(INTERNAL_LIGHT_ZONE, "spectrum", "Internal spectrum")

    async def internal_breathing(
        self,
        r: int = 0,
        g: int = 0,
        b: int = 0,
        *,
        r2: int | None = None,
        g2: int | None = None,
        b2: int | None = None,
    ) -> CommandResult:
        return await self._send_effect(
            INTERNAL_LIGHT_ZONE,
            "breathing",
            "Internal breathing",
            r=r,
            g=g,
            b=b,
            r2=r2,
            g2=g2,
            b2=b2,
        )

    async def internal_off(self) -> CommandResult:
        return await self._send_effect(INTERNAL_LIGHT_ZONE, "off", "Internal off")

    # --- 3. External lighting ---

    async def external_static(self, r: int, g: int, b: int) -> CommandResult:
        return await self._send_effect(
            EXTERNAL_LIGHT_ZONE,
            "static",
            f"External static #{r:02X}{g:02X}{b:02X}",
            r=r,
            g=g,
            b=b,
        )

    async def external_spectrum(self) -> CommandResult:
        return await self._send_effect(EXTERNAL_LIGHT_ZONE, "spectrum", "External spectrum")

    async def external_breathing(
        self,
        r: int = 0,
        g: int = 0,
        b: int = 0,
        *,
        r2: int | None = None,
        g2: int | None = None,
        b2: int | None = None,
    ) -> CommandResult:
        return await self._send_effect(
            EXTERNAL_LIGHT_ZONE,
            "breathing",
            "External breathing",
            r=r,
            g=g,
            b=b,
            r2=r2,
            g2=g2,
            b2=b2,
        )

    async def external_wave(
        self,
        *,
        left_to_right: bool = True,
        rate: int = WAVE_RATE_FACTORY,
    ) -> CommandResult:
        direction = "LTR" if left_to_right else "RTL"
        return await self._send_effect(
            EXTERNAL_LIGHT_ZONE,
            "wave",
            f"External wave {direction} rate {rate}",
            wave_left_to_right=left_to_right,
            wave_rate=rate,
        )

    async def external_off(self) -> CommandResult:
        return await self._send_effect(EXTERNAL_LIGHT_ZONE, "off", "External off")
