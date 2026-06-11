"""Hazel APK packet builders for fan and lighting (product API)."""

from __future__ import annotations

from zephyr_re.constants import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE
from zephyr_re.protocol.base import FanSpeed

FAN_LEVEL: dict[FanSpeed, int] = {
    FanSpeed.OFF: 0,
    FanSpeed.LOW: 1,
    FanSpeed.HIGH: 2,
}

EFFECT_TYPE: dict[str, int] = {
    "off": 0,
    "static": 1,
    "breathing": 2,
    "spectrum": 3,
    "wave": 4,
}

WAVE_RATE_FACTORY = 90
WAVE_RATE_SLOW = 15
WAVE_RATE_MEDIUM = 50
WAVE_RATE_FAST = 100

WAVE_SPEED_PRESETS: dict[str, int] = {
    "factory": WAVE_RATE_FACTORY,
    "slow": WAVE_RATE_SLOW,
    "medium": WAVE_RATE_MEDIUM,
    "fast": WAVE_RATE_FAST,
}


def effect_set_header(req_id: int, payload: bytes, *, sub_id: int = 0, zone: int) -> bytes:
    plen = len(payload)
    return bytes(
        [
            req_id & 0xFF,
            plen & 0xFF,
            (plen >> 8) & 0xFF,
            (plen >> 16) & 0xFF,
            0x10,
            0x03,
            sub_id & 0xFF,
            zone & 0xFF,
        ]
    )


def ble_effect_configuration(
    effect_type: int,
    param1: int = 0,
    param2: int = 0,
    *,
    color1: tuple[int, int, int] | None = None,
    color2: tuple[int, int, int] | None = None,
) -> bytes:
    body = [effect_type & 0xFF, param1 & 0xFF, param2 & 0xFF]
    if color1 is None and color2 is None:
        body.append(0)
    elif color1 is not None and color2 is None:
        body.append(1)
        body.extend(c & 0xFF for c in color1)
    else:
        body.append(2)
        if color1 is not None:
            body.extend(c & 0xFF for c in color1)
        if color2 is not None:
            body.extend(c & 0xFF for c in color2)
    return bytes(body)


def effect_off_v3_packets(
    req_id: int,
    zone: int,
    *,
    sub_id: int = 0,
) -> tuple[bytes, bytes]:
    payload = b"\x00"
    return effect_set_header(req_id, payload, sub_id=sub_id, zone=zone), payload


def effect_packets(
    req_id: int,
    effect: str,
    zone: int,
    *,
    sub_id: int = 0,
    r: int = 0,
    g: int = 0,
    b: int = 0,
    r2: int | None = None,
    g2: int | None = None,
    b2: int | None = None,
    wave_left_to_right: bool = True,
    wave_rate: int = WAVE_RATE_FACTORY,
) -> tuple[bytes, bytes]:
    name = effect.lower()
    effect_type = EFFECT_TYPE.get(name)
    if effect_type is None:
        raise ValueError(f"Unknown effect: {effect}")

    if effect_type == 0:
        return effect_off_v3_packets(req_id, zone, sub_id=sub_id)
    if effect_type == 1:
        payload = ble_effect_configuration(1, 0, 0, color1=(r & 0xFF, g & 0xFF, b & 0xFF))
    elif effect_type == 2:
        c1 = (r & 0xFF, g & 0xFF, b & 0xFF) if (r or g or b) else None
        c2 = None
        if r2 is not None and g2 is not None and b2 is not None:
            c2 = (r2 & 0xFF, g2 & 0xFF, b2 & 0xFF)
        payload = ble_effect_configuration(2, 0, 0, color1=c1, color2=c2)
    elif effect_type == 3:
        payload = ble_effect_configuration(3, 0, 0)
    elif effect_type == 4:
        direction = 1 if wave_left_to_right else 2
        payload = ble_effect_configuration(4, direction, wave_rate & 0xFF)
    else:
        raise ValueError(f"Unsupported effect type: {effect_type}")

    return effect_set_header(req_id, payload, sub_id=sub_id, zone=zone), payload


def fan_speed_packets(req_id: int, speed: FanSpeed) -> tuple[bytes, bytes]:
    level = FAN_LEVEL[speed]
    header = bytes([req_id & 0xFF, 0x06, 0x00, 0x00, 0x11, 0x01, 0x01, 0x00])
    payload = bytes([0x01, 0x00, level & 0xFF, 0x00, level & 0xFF, 0x00])
    return header, payload


__all__ = [
    "EFFECT_TYPE",
    "EXTERNAL_LIGHT_ZONE",
    "INTERNAL_LIGHT_ZONE",
    "WAVE_RATE_FACTORY",
    "WAVE_SPEED_PRESETS",
    "effect_packets",
    "fan_speed_packets",
]
