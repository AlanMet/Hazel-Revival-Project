"""Probe Razer open-snek vendor GATT protocol on connected devices."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
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
from zephyr_re_dev.protocol.hazel_write import (
    WAVE_RATE_FACTORY,
    brightness_packets,
    effect_packets,
    fan_speed_packets,
    internal_light_packets,
    static_color_packets,
)
from zephyr_re_dev.protocol.zephyr_parse import (
    EXTERNAL_LIGHT_ZONE,
    INTERNAL_LIGHT_ZONE,
    is_vendor_response,
    parse_brightness,
    parse_color,
    parse_effect,
)
from zephyr_re.util.hexio import format_hex

# From open-snek BLE_PROTOCOL.md
RAZER_VENDOR_SERVICE = "52401523-F97C-7F90-0E7F-6C6F4E36DB1C"
RAZER_VENDOR_WRITE = "52401524-F97C-7F90-0E7F-6C6F4E36DB1C"
RAZER_VENDOR_NOTIFY = "52401525-F97C-7F90-0E7F-6C6F4E36DB1C"
RAZER_VENDOR_NOTIFY_EXTRA = "52401526-F97C-7F90-0E7F-6C6F4E36DB1C"
STANDARD_BATTERY_CHAR = "00002a19-0000-1000-8000-00805f9b34fb"
NOTIFY_TIMEOUT_MS = 1500

KEY_READ_BATTERY = bytes([0x05, 0x81, 0x00, 0x01])
KEY_READ_COLOR = bytes([0x10, 0x84, 0x00, 0x00])
KEY_READ_BRIGHTNESS = bytes([0x10, 0x85, 0x01, 0x01])
KEY_READ_EFFECT = bytes([0x10, 0x83, 0x00, 0x00])
# Hazel.java — per-zone chroma + device info
KEY_READ_FAN = bytes([0x11, 0x81, 0x01, 0x00])
KEY_READ_FIRMWARE = bytes([0x00, 0x81, 0x00, 0x00])
KEY_READ_CHARGING = bytes([0x05, 0x85, 0x00, 0x00])


def _zone_brightness_key(zone: int) -> bytes:
    return bytes([0x10, 0x85, 0x00, zone])


def _zone_effect_key(zone: int) -> bytes:
    return bytes([0x10, 0x83, 0x00, zone])
STATUS_SUCCESS = 0x02

VENDOR_READ_GAP_S = 0.15


@dataclass(frozen=True)
class VendorSyncRaw:
    brightness_external: list[bytes]
    brightness_internal: list[bytes]
    effect_external: list[bytes]
    effect_internal: list[bytes]
    fan: list[bytes]
    firmware: list[bytes]
    charging: list[bytes]
    extra: list[bytes]
    brightness_external_req: int
    brightness_internal_req: int


class RazerVendorProbe(ProtocolBackend):
    name = "razer_probe"

    def __init__(self) -> None:
        self._client: BleClient | None = None
        self._req_id = 0x30
        self._available = False

    @property
    def available(self) -> bool:
        return self._available

    async def on_connect(self, client: BleClient) -> None:
        self._client = client
        svc = client.find_service(RAZER_VENDOR_SERVICE)
        write = client.find_characteristic(RAZER_VENDOR_WRITE)
        notify = client.find_characteristic(RAZER_VENDOR_NOTIFY)
        self._available = svc is not None and write is not None and notify is not None
        if self._available:
            await client.start_notify(RAZER_VENDOR_NOTIFY)
            # Zephyr exposes an extra notify char (52401526)
            extra = client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA)
            if extra is not None:
                try:
                    await client.start_notify(extra.uuid)
                except Exception as exc:
                    client.capture.log("info", message=f"[razer_probe] extra notify subscribe: {exc}")
            client.capture.log(
                "info",
                message="[razer_probe] Razer vendor GATT service detected",
            )
        else:
            client.capture.log(
                "info",
                message="[razer_probe] Razer vendor GATT not found on this device",
            )

    def _next_req_id(self) -> int:
        rid = self._req_id
        self._req_id = (self._req_id + 1) & 0xFF
        return rid

    def _build_read_header(self, key: bytes) -> bytes:
        return bytes([self._next_req_id(), 0x00, 0x00, 0x00]) + key

    def _notify_uuids(self) -> list[str]:
        if not self._client:
            return []
        uuids = [RAZER_VENDOR_NOTIFY]
        if self._client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA) is not None:
            uuids.append(RAZER_VENDOR_NOTIFY_EXTRA)
        return uuids

    async def _collect_notifications(self, *, timeout_ms: int = NOTIFY_TIMEOUT_MS) -> list[bytes]:
        """Wait for replies on primary + extra notify chars (caller clears before write)."""
        if not self._client:
            return []
        frames = await self._client.wait_for_notifications(
            RAZER_VENDOR_NOTIFY,
            timeout_ms,
            clear_first=False,
        )
        for uuid in self._notify_uuids():
            if uuid.lower() != RAZER_VENDOR_NOTIFY.lower():
                frames.extend(self._client.drain_notifications(uuid))
        return frames

    def _drain_extra_notifications(self) -> list[bytes]:
        if not self._client:
            return []
        extra = self._client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA)
        if extra is None:
            return []
        return self._client.drain_notifications(extra.uuid)

    async def _exchange(self, header: bytes, payload: bytes = b"") -> list[bytes]:
        if not self._client or not self._available:
            return []
        for uuid in self._notify_uuids():
            self._client.clear_notifications(uuid)
        if payload:
            # open-snek: header ATT write, then payload as a second write
            await self._client.write(RAZER_VENDOR_WRITE, header, response=True)
            await self._client.write(RAZER_VENDOR_WRITE, payload, response=True)
        else:
            await self._client.write(RAZER_VENDOR_WRITE, header, response=True)
        return await self._collect_notifications()

    def _command_result(
        self,
        label: str,
        frames: list[bytes],
        *,
        ok_detail: str,
    ) -> CommandResult:
        if self._client:
            if self._parse_status(frames):
                self._client.capture.log_command_result(label, ok_detail, frames)
                return CommandResult(CommandStatus.OK, ok_detail, frames)
            if frames:
                hex_frames = "; ".join(format_hex(f) for f in frames[:3])
                msg = f"{label} — sent, unexpected reply: {hex_frames}"
                self._client.capture.log_command_result(label, msg, frames)
                return CommandResult(CommandStatus.PARTIAL, msg, frames)
            msg = (
                f"{label} — sent, no notify ack "
                "(Zephyr protocol not decoded; mask likely ignored it)"
            )
            self._client.capture.log_command_result(label, msg, frames)
            return CommandResult(CommandStatus.PARTIAL, msg, frames)
        if self._parse_status(frames):
            return CommandResult(CommandStatus.OK, ok_detail, frames)
        if frames:
            hex_frames = "; ".join(format_hex(f) for f in frames[:3])
            return CommandResult(
                CommandStatus.PARTIAL,
                f"{label} — sent, unexpected reply: {hex_frames}",
                frames,
            )
        return CommandResult(
            CommandStatus.PARTIAL,
            f"{label} — sent, no notify ack (Zephyr protocol not decoded; mask likely ignored it)",
            frames,
        )

    def _parse_status(self, frames: list[bytes]) -> bool:
        return is_vendor_response(frames)

    def _parse_battery(self, frames: list[bytes]) -> int | None:
        for frame in frames:
            if len(frame) >= 9 and frame[7] == STATUS_SUCCESS:
                if frame[1] > 0 and len(frame) > 8:
                    val = frame[8]
                    return val if val <= 100 else round(val * 100 / 255)
            # continuation frame
            if len(frame) >= 1:
                val = frame[0]
                if val <= 100:
                    return val
        return None

    def _parse_color(self, frames: list[bytes]) -> ColorInfo | None:
        color, _note = parse_color(frames)
        return color

    async def _read_standard_battery(self) -> BatteryInfo | None:
        if not self._client:
            return None
        if self._client.find_characteristic(STANDARD_BATTERY_CHAR) is None:
            return None
        try:
            data = await self._client.read(STANDARD_BATTERY_CHAR)
        except Exception as exc:
            self._client.capture.log("info", message=f"[razer_probe] standard battery read: {exc}")
            return None
        if not data:
            return None
        pct = data[0]
        if pct > 100:
            pct = round(pct * 100 / 255)
        return BatteryInfo(percent=pct, raw=bytes(data), message=None)

    async def read_battery(self) -> BatteryInfo | None:
        standard = await self._read_standard_battery()
        if standard is not None and standard.percent is not None:
            return standard
        if not self._available:
            return BatteryInfo(percent=None, message="Razer vendor service not available")
        header = self._build_read_header(KEY_READ_BATTERY)
        frames = await self._exchange(header)
        pct = self._parse_battery(frames)
        return BatteryInfo(
            percent=pct,
            raw=frames[0] if frames else None,
            message=None if pct is not None else f"No parseable battery in {format_hex(frames[0]) if frames else 'no response'}",
        )

    async def read_external_color(self) -> ColorInfo | None:
        if not self._available:
            return None
        header = self._build_read_header(KEY_READ_COLOR)
        frames = await self._exchange(header)
        return self._parse_color(frames)

    async def read_external_brightness(self) -> int | None:
        if not self._available:
            return None
        header = self._build_read_header(KEY_READ_BRIGHTNESS)
        frames = await self._exchange(header)
        return parse_brightness(frames)

    async def read_external_effect(self) -> str | None:
        if not self._available:
            return None
        header = self._build_read_header(KEY_READ_EFFECT)
        frames = await self._exchange(header)
        return parse_effect(frames)

    async def read_external_color_with_note(self) -> tuple[ColorInfo | None, str | None]:
        if not self._available:
            return None, None
        header = self._build_read_header(KEY_READ_COLOR)
        frames = await self._exchange(header)
        return parse_color(frames)

    async def read_vendor_sync_raw(self) -> VendorSyncRaw | None:
        """Hazel APK read set: per-zone chroma, fan, firmware, charging."""
        if not self._available:
            return None
        bright_ext_hdr = self._build_read_header(_zone_brightness_key(EXTERNAL_LIGHT_ZONE))
        brightness_external = await self._exchange(bright_ext_hdr)
        await asyncio.sleep(VENDOR_READ_GAP_S)
        bright_int_hdr = self._build_read_header(_zone_brightness_key(INTERNAL_LIGHT_ZONE))
        brightness_internal = await self._exchange(bright_int_hdr)
        await asyncio.sleep(VENDOR_READ_GAP_S)
        effect_external = await self._exchange(
            self._build_read_header(_zone_effect_key(EXTERNAL_LIGHT_ZONE))
        )
        await asyncio.sleep(VENDOR_READ_GAP_S)
        effect_internal = await self._exchange(
            self._build_read_header(_zone_effect_key(INTERNAL_LIGHT_ZONE))
        )
        await asyncio.sleep(VENDOR_READ_GAP_S)
        fan = await self._exchange(self._build_read_header(KEY_READ_FAN))
        await asyncio.sleep(VENDOR_READ_GAP_S)
        firmware = await self._exchange(self._build_read_header(KEY_READ_FIRMWARE))
        await asyncio.sleep(VENDOR_READ_GAP_S)
        charging = await self._exchange(self._build_read_header(KEY_READ_CHARGING))
        extra = self._drain_extra_notifications()
        return VendorSyncRaw(
            brightness_external=brightness_external,
            brightness_internal=brightness_internal,
            effect_external=effect_external,
            effect_internal=effect_internal,
            fan=fan,
            firmware=firmware,
            charging=charging,
            extra=extra,
            brightness_external_req=bright_ext_hdr[0],
            brightness_internal_req=bright_int_hdr[0],
        )

    async def set_external_color(self, r: int, g: int, b: int) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        header, payload = static_color_packets(req, r, g, b, EXTERNAL_LIGHT_ZONE)
        frames = await self._exchange(header, payload)
        return self._command_result(
            "Set external color",
            frames,
            ok_detail=f"Set external color zone 0x{EXTERNAL_LIGHT_ZONE:02X} #{r:02X}{g:02X}{b:02X}",
        )

    async def set_external_brightness(self, brightness: int) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        header, payload = brightness_packets(req, brightness, EXTERNAL_LIGHT_ZONE)
        frames = await self._exchange(header, payload)
        return self._command_result(
            "Set brightness",
            frames,
            ok_detail=f"Set external brightness {brightness} (zone 0x{EXTERNAL_LIGHT_ZONE:02X})",
        )

    async def set_external_effect(self, effect: str, **opts: Any) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        try:
            header, payload = effect_packets(
                req,
                effect,
                EXTERNAL_LIGHT_ZONE,
                r=int(opts.get("r", 0)),
                g=int(opts.get("g", 0)),
                b=int(opts.get("b", 0)),
                r2=opts.get("r2"),
                g2=opts.get("g2"),
                b2=opts.get("b2"),
                wave_left_to_right=bool(opts.get("wave_left_to_right", True)),
                wave_rate=int(opts.get("wave_rate", WAVE_RATE_FACTORY)),
            )
        except ValueError as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))
        frames = await self._exchange(header, payload)
        detail = f"Set external effect {effect} (zone 0x{EXTERNAL_LIGHT_ZONE:02X})"
        if effect.lower() == "wave":
            rate = int(opts.get("wave_rate", WAVE_RATE_FACTORY))
            detail += f", wave rate {rate}"
        return self._command_result("Set effect", frames, ok_detail=detail)

    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0) -> CommandResult:
        """Mouth zone 0x01 — Hazel applyFirmwareEffect / createOffEffect."""
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        header, payload = internal_light_packets(req, on, r, g, b)
        frames = await self._exchange(header, payload)
        if on and r == 0 and g == 0 and b == 0:
            r, g, b = 0, 255, 0
        state = "on" if on else "off"
        return self._command_result(
            "Set internal light",
            frames,
            ok_detail=f"Set internal light {state} zone 0x{INTERNAL_LIGHT_ZONE:02X} #{r:02X}{g:02X}{b:02X}",
        )

    async def set_internal_brightness(self, brightness: int) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        header, payload = brightness_packets(req, brightness, INTERNAL_LIGHT_ZONE)
        frames = await self._exchange(header, payload)
        return self._command_result(
            "Set brightness",
            frames,
            ok_detail=f"Set internal brightness {brightness} (zone 0x{INTERNAL_LIGHT_ZONE:02X})",
        )

    async def set_internal_effect(self, effect: str, **opts: Any) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        if effect.lower() == "wave":
            return CommandResult(CommandStatus.ERROR, "Wave is external zone (0x05) only")
        req = self._next_req_id()
        try:
            header, payload = effect_packets(
                req,
                effect,
                INTERNAL_LIGHT_ZONE,
                r=int(opts.get("r", 0)),
                g=int(opts.get("g", 0)),
                b=int(opts.get("b", 0)),
                r2=opts.get("r2"),
                g2=opts.get("g2"),
                b2=opts.get("b2"),
            )
        except ValueError as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))
        frames = await self._exchange(header, payload)
        return self._command_result(
            "Set effect",
            frames,
            ok_detail=f"Set internal effect {effect} (zone 0x{INTERNAL_LIGHT_ZONE:02X})",
        )

    async def set_fan_speed(self, speed: FanSpeed) -> CommandResult:
        if not self._available:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Razer vendor service not available")
        req = self._next_req_id()
        header, payload = fan_speed_packets(req, speed)
        frames = await self._exchange(header, payload)
        return self._command_result(
            "Set fan speed",
            frames,
            ok_detail=f"Set fan speed {speed.value} (level {payload[2]})",
        )

    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        from zephyr_re.util.hexio import parse_hex

        target = char_uuid or RAZER_VENDOR_WRITE
        data = parse_hex(write_hex)
        try:
            frames = await self._client.exchange(
                target,
                data,
                RAZER_VENDOR_NOTIFY if target == RAZER_VENDOR_WRITE else None,
                timeout_ms=500,
            )
            return CommandResult(CommandStatus.OK, "Raw exchange complete", frames)
        except Exception as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))
