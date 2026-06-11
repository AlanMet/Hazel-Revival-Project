"""Aggregated device state for sync and UI."""

from __future__ import annotations

from dataclasses import dataclass, field

from zephyr_re.protocol.base import ColorInfo, FanSpeed


@dataclass
class DeviceState:
    battery_percent: int | None = None
    external_brightness: int | None = None
    external_brightness_percent: int | None = None
    internal_brightness: int | None = None
    internal_brightness_percent: int | None = None
    external_effect: str | None = None
    external_color_note: str | None = None
    internal_effect: str | None = None
    fan_speed: FanSpeed = FanSpeed.OFF
    fan_speed_source: str = "assumed"
    internal_light_on: bool | None = None
    internal_light_color: ColorInfo | None = None
    firmware_version: str | None = None
    is_charging: bool | None = None
    synced_at: str = ""
