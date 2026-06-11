"""Public Zephyr control API — one method per Hazel app feature."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from zephyr_re.ble.connector import ZephyrConnector
from zephyr_re.ble.scanner import BleDevice, scan_devices
from zephyr_re.device.state import DeviceState
from zephyr_re.protocol.base import CommandResult, CommandStatus, FanSpeed
from zephyr_re.constants import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE
from zephyr_re.protocol.parse import (
    brightness_to_percent,
    parse_charging_state,
    parse_extra_fan,
    parse_firmware_version,
    resolve_brightness,
    resolve_fan_speed,
    resolve_internal_light,
    resolve_zone_chroma,
)
from zephyr_re.protocol.packets import (
    WAVE_RATE_FACTORY,
    effect_packets,
    fan_speed_packets,
)
from zephyr_re.protocol.sync import VendorSync
from zephyr_re.util.hexio import format_hex


class Zephyr:
    """Control a Razer Zephyr over BLE.

    Transport is ``ZephyrConnector``; this class only builds packets and maps
    replies to ``CommandResult``. Safe to import from a future GUI app.
    """

    def __init__(self, connector: ZephyrConnector | None = None) -> None:
        self._conn = connector or ZephyrConnector()
        self._req_id = 0x30
        self._last_state: DeviceState | None = None
        self._on_fan_notify: Callable[[FanSpeed], None] | None = None

    @property
    def connector(self) -> ZephyrConnector:
        return self._conn

    @property
    def is_connected(self) -> bool:
        return self._conn.is_connected

    @property
    def last_state(self) -> DeviceState | None:
        return self._last_state

    def on_fan_notify(self, callback: Callable[[FanSpeed], None] | None) -> None:
        self._on_fan_notify = callback

    async def scan(self, *, timeout: float = 8.0) -> list[BleDevice]:
        return await scan_devices(timeout, name_patterns=self._conn._patterns)

    async def connect(self) -> str:
        """Auto-find and connect. Returns device address."""
        addr = await self._conn.connect_foolproof()
        await self._after_connect()
        return addr

    async def connect_to(self, device: BleDevice) -> str:
        addr = await self._conn.connect_to(device)
        await self._after_connect()
        return addr

    async def disconnect(self) -> None:
        await self._conn.disconnect()
        self._last_state = None

    async def _after_connect(self) -> None:
        client = self._conn.client
        if client is None:
            return
        from zephyr_re.constants import RAZER_VENDOR_NOTIFY_EXTRA

        def _status_handler(data: bytes) -> None:
            speed = parse_extra_fan(data)
            if speed is None:
                return
            if self._last_state is not None:
                self._last_state.fan_speed = speed
                self._last_state.fan_speed_source = "notify"
            if self._on_fan_notify is not None:
                self._on_fan_notify(speed)

        if client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA) is not None:
            client.add_notify_handler(RAZER_VENDOR_NOTIFY_EXTRA, _status_handler)

    async def sync_state(self) -> DeviceState:
        """Read battery, fan, lighting, firmware from connected mask."""
        client = self._conn.client
        if client is None or not self._conn.is_connected:
            raise RuntimeError("Not connected")

        sync = VendorSync(client)
        battery = await sync.read_standard_battery()
        raw = await sync.read_vendor_sync_raw()

        if raw is None:
            raise RuntimeError("Vendor sync failed — Razer GATT not available")

        external_zone = resolve_zone_chroma(raw.effect_external)
        internal_zone = resolve_zone_chroma(raw.effect_internal)
        internal_on, internal_color = resolve_internal_light(raw.effect_internal)
        fan_speed, fan_source = resolve_fan_speed(raw.fan, raw.extra)
        ext_brightness = resolve_brightness(
            raw.brightness_external,
            raw.extra,
            header_req=raw.brightness_external_req,
        )
        int_brightness = resolve_brightness(
            raw.brightness_internal,
            raw.extra,
            header_req=raw.brightness_internal_req,
        )

        state = DeviceState(
            battery_percent=battery.percent if battery else None,
            external_brightness=ext_brightness,
            external_brightness_percent=(
                brightness_to_percent(ext_brightness) if ext_brightness is not None else None
            ),
            internal_brightness=int_brightness,
            internal_brightness_percent=(
                brightness_to_percent(int_brightness) if int_brightness is not None else None
            ),
            external_effect=external_zone.effect if external_zone.effect != "unknown" else None,
            external_color_note=external_zone.color_note,
            internal_effect=internal_zone.effect if internal_zone.effect != "unknown" else None,
            fan_speed=fan_speed,
            fan_speed_source=fan_source,
            internal_light_on=internal_on,
            internal_light_color=internal_color,
            firmware_version=parse_firmware_version(raw.firmware),
            is_charging=parse_charging_state(raw.charging),
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
        self._last_state = state
        return state

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
