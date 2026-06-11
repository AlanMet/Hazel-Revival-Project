"""Vendor read/sync exchange for device state."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from zephyr_re.ble.client import BleClient
from zephyr_re.constants import (
    BATTERY_CHAR_UUID,
    EXTERNAL_LIGHT_ZONE,
    INTERNAL_LIGHT_ZONE,
    RAZER_VENDOR_NOTIFY,
    RAZER_VENDOR_NOTIFY_EXTRA,
    RAZER_VENDOR_WRITE,
)
from zephyr_re.protocol.base import BatteryInfo

VENDOR_READ_GAP_S = 0.15

KEY_READ_FAN = bytes([0x11, 0x81, 0x01, 0x00])
KEY_READ_FIRMWARE = bytes([0x00, 0x81, 0x00, 0x00])
KEY_READ_CHARGING = bytes([0x05, 0x85, 0x00, 0x00])


def _zone_brightness_key(zone: int) -> bytes:
    return bytes([0x10, 0x85, 0x00, zone])


def _zone_effect_key(zone: int) -> bytes:
    return bytes([0x10, 0x83, 0x00, zone])


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


class VendorSync:
    """Read vendor state from connected peripheral."""

    def __init__(self, client: BleClient, *, req_id_start: int = 0x30) -> None:
        self._client = client
        self._req_id = req_id_start

    def _next_req_id(self) -> int:
        rid = self._req_id
        self._req_id = (self._req_id + 1) & 0xFF
        return rid

    def _build_read_header(self, key: bytes) -> bytes:
        return bytes([self._next_req_id(), 0x00, 0x00, 0x00]) + key

    def _notify_uuids(self) -> list[str]:
        uuids = [RAZER_VENDOR_NOTIFY]
        if self._client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA) is not None:
            uuids.append(RAZER_VENDOR_NOTIFY_EXTRA)
        return uuids

    async def _collect_notifications(self, *, timeout_ms: int = 1500) -> list[bytes]:
        frames = await self._client.wait_for_notifications(
            RAZER_VENDOR_NOTIFY,
            timeout_ms,
            clear_first=False,
        )
        for uuid in self._notify_uuids():
            if uuid.lower() != RAZER_VENDOR_NOTIFY.lower():
                frames.extend(self._client.drain_notifications(uuid))
        return frames

    async def _exchange(self, header: bytes) -> list[bytes]:
        for uuid in self._notify_uuids():
            self._client.clear_notifications(uuid)
        await self._client.write(RAZER_VENDOR_WRITE, header, response=True)
        return await self._collect_notifications()

    async def read_standard_battery(self) -> BatteryInfo | None:
        if self._client.find_characteristic(BATTERY_CHAR_UUID) is None:
            return None
        try:
            data = await self._client.read(BATTERY_CHAR_UUID)
        except Exception:
            return None
        if not data:
            return None
        pct = data[0]
        if pct > 100:
            pct = round(pct * 100 / 255)
        return BatteryInfo(percent=pct, raw=bytes(data))

    async def read_vendor_sync_raw(self) -> VendorSyncRaw | None:
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
        extra = []
        extra_char = self._client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA)
        if extra_char is not None:
            extra = self._client.drain_notifications(extra_char.uuid)
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
