"""Aggregated device state for sync and future UI."""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr_re_dev.ble.gatt_read import GattReadResult
from zephyr_re.protocol.base import ColorInfo, FanSpeed


@dataclass
class DeviceState:
    battery_percent: int | None = None
    external_brightness: int | None = None
    external_brightness_percent: int | None = None
    internal_brightness: int | None = None
    internal_brightness_percent: int | None = None
    external_color: ColorInfo | None = None
    external_effect: str | None = None
    external_color_note: str | None = None
    internal_effect: str | None = None
    fan_speed: FanSpeed = FanSpeed.OFF
    fan_speed_source: str = "assumed"
    internal_light: str = "unknown"
    internal_light_on: bool | None = None
    internal_light_color: ColorInfo | None = None
    internal_light_zone: int | None = None
    firmware_version: str | None = None
    is_charging: bool | None = None
    gatt_reads: list[GattReadResult] = field(default_factory=list)
    vendor_raw: dict[str, list[bytes]] = field(default_factory=dict)
    extra_raw: list[bytes] = field(default_factory=list)
    synced_at: str = ""
