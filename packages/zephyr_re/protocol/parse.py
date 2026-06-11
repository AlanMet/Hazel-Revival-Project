"""Decode Razer Zephyr vendor notify frames."""

from __future__ import annotations

from dataclasses import dataclass

from zephyr_re.protocol.base import ColorInfo, FanSpeed

STATUS_OK = 0x02
STATUS_DATA = 0x07

EFFECT_ID_TO_NAME: dict[int, str] = {
    0: "static",
    1: "breathing",
    8: "spectrum",
}

HAZEL_EFFECT_BY_ID: dict[int, str] = {
    0: "off",
    1: "static",
    2: "breathing",
    3: "spectrum",
    4: "wave",
    7: "starlight",
}

FAN_EXTRA_MAP: dict[int, FanSpeed] = {
    0: FanSpeed.OFF,
    1: FanSpeed.LOW,
    2: FanSpeed.HIGH,
}

DEFAULT_EFFECT = "spectrum"
ANIMATED_COLOR_NOTE = "No fixed color (animated effect)"
EXTRA_BRIGHTNESS_PREFIX = (0x05, 0x31)
EXTRA_FAN_PREFIX = (0x05, 0x39)
EXTERNAL_LIGHT_ZONE = 0x05
INTERNAL_LIGHT_ZONE = 0x01
DEFAULT_INTERNAL_GREEN = ColorInfo(0, 255, 0)


@dataclass
class ZoneChromaState:
    effect: str = "unknown"
    color: ColorInfo | None = None
    color_note: str | None = None
    on: bool | None = None


def _payload_after_header(frame: bytes) -> bytes:
    if len(frame) <= 8:
        return b""
    return frame[8:]


def _is_device_token_only(payload: bytes) -> bool:
    return len(payload) == 12


def brightness_to_percent(value: int) -> int:
    if value <= 100:
        return value
    return round(value * 100 / 255)


def parse_brightness(frames: list[bytes], *, header_req: int | None = None) -> int | None:
    candidates: list[int] = []
    for frame in frames:
        if len(frame) < 8 or frame[7] != STATUS_OK:
            continue
        val = frame[0]
        if header_req is not None and val == header_req:
            continue
        if 0 <= val <= 255:
            candidates.append(val)
    if candidates:
        return candidates[-1]
    return None


def parse_extra_brightness(frame: bytes) -> int | None:
    if len(frame) >= 3 and frame[0] == EXTRA_BRIGHTNESS_PREFIX[0] and frame[1] == EXTRA_BRIGHTNESS_PREFIX[1]:
        return frame[2]
    return None


def parse_extra_fan(frame: bytes) -> FanSpeed | None:
    if len(frame) >= 3 and frame[0] == EXTRA_FAN_PREFIX[0] and frame[1] == EXTRA_FAN_PREFIX[1]:
        return FAN_EXTRA_MAP.get(frame[2])
    return None


def latest_fan_from_frames(frames: list[bytes]) -> FanSpeed | None:
    for frame in reversed(frames):
        speed = parse_extra_fan(frame)
        if speed is not None:
            return speed
    return None


def parse_fan_speed_read(frames: list[bytes]) -> FanSpeed | None:
    for frame in frames:
        if len(frame) >= 3 and frame[2] in FAN_EXTRA_MAP:
            return FAN_EXTRA_MAP[frame[2]]
    return None


def resolve_fan_speed(
    fan_read_frames: list[bytes],
    extra_frames: list[bytes],
) -> tuple[FanSpeed, str]:
    speed = parse_fan_speed_read(fan_read_frames)
    if speed is not None:
        return speed, "read"
    speed = latest_fan_from_frames(extra_frames)
    if speed is not None:
        return speed, "notify"
    return FanSpeed.OFF, "assumed"


def parse_firmware_version(frames: list[bytes]) -> str | None:
    for frame in frames:
        if len(frame) >= 8 and frame[7] == STATUS_OK:
            tail = _payload_after_header(frame)
            if len(tail) >= 4 and not _is_device_token_only(tail):
                return _format_fw_bytes(tail[:4])
    for frame in frames:
        if len(frame) >= 4 and frame[0] < 0x10 and all(b <= 99 for b in frame[:4]):
            return _format_fw_bytes(frame[:4])
    return None


def _format_fw_bytes(chunk: bytes) -> str:
    return f"{chunk[0]:02d}.{chunk[1]:02d}.{chunk[2]:02d}.{chunk[3]:02d}"


def parse_charging_state(frames: list[bytes]) -> bool | None:
    for frame in frames:
        if len(frame) >= 1 and frame[7] == STATUS_OK:
            tail = _payload_after_header(frame)
            if tail:
                return tail[0] != 0
        if len(frame) >= 1 and frame[7] not in (STATUS_OK, STATUS_DATA):
            return frame[0] != 0
    return None


def parse_hazel_effect_body(body: bytes) -> ZoneChromaState:
    if not body:
        return ZoneChromaState()
    effect_id = body[0]
    name = HAZEL_EFFECT_BY_ID.get(effect_id, f"unknown({effect_id})")
    if effect_id == 0:
        return ZoneChromaState(effect=name, on=False)
    if effect_id == 1 and len(body) >= 7:
        return ZoneChromaState(
            effect=name,
            on=True,
            color=ColorInfo(r=body[4], g=body[5], b=body[6], raw=body),
        )
    if effect_id == 2 and len(body) >= 7:
        return ZoneChromaState(
            effect=name,
            on=True,
            color=ColorInfo(r=body[4], g=body[5], b=body[6], raw=body),
            color_note="breathing (first color)",
        )
    if effect_id == 3:
        return ZoneChromaState(effect=name, on=True, color_note=ANIMATED_COLOR_NOTE)
    if effect_id == 4:
        note = "wave"
        if len(body) >= 3:
            direction = "LTR" if body[1] == 1 else "RTL"
            note = f"wave ({direction}, rate {body[2]})"
        return ZoneChromaState(effect=name, on=True, color_note=note)
    return ZoneChromaState(effect=name)


def parse_zone_chroma_effect(frames: list[bytes]) -> ZoneChromaState:
    for frame in frames:
        if len(frame) >= 8 and frame[7] == STATUS_OK:
            tail = _payload_after_header(frame)
            if tail and not _is_device_token_only(tail) and tail[0] in HAZEL_EFFECT_BY_ID:
                return parse_hazel_effect_body(tail)
        for start in (0, 1):
            if len(frame) < start + 1:
                continue
            chunk = frame[start : start + 16]
            if chunk[0] in HAZEL_EFFECT_BY_ID:
                return parse_hazel_effect_body(chunk)
    return ZoneChromaState()


def resolve_zone_chroma(frames: list[bytes]) -> ZoneChromaState:
    chroma = parse_zone_chroma_effect(frames)
    if chroma.effect != "unknown":
        return chroma
    on, color = parse_zone_static_state(frames)
    if on is False:
        return ZoneChromaState(effect="off", on=False)
    if on is True or color is not None:
        return ZoneChromaState(effect="static", on=on, color=color)
    return ZoneChromaState()


def _parse_zone_body(body: bytes) -> tuple[bool | None, ColorInfo | None] | None:
    if len(body) < 7 or body[0] not in (0x00, 0x01):
        return None
    marker = body[1:4]
    if marker not in (bytes([0x00, 0x00, 0x01]), bytes([0x01, 0x00, 0x01])):
        return None
    enabled = body[0] == 0x01
    return enabled, ColorInfo(
        r=body[4],
        g=body[5],
        b=body[6],
        raw=body[:10] if len(body) >= 10 else body,
    )


def parse_zone_static_state(frames: list[bytes]) -> tuple[bool | None, ColorInfo | None]:
    for frame in frames:
        if len(frame) >= 8 and frame[7] == STATUS_OK:
            parsed = _parse_zone_body(_payload_after_header(frame))
            if parsed is not None:
                return parsed
    for frame in frames:
        for start in (0, 1):
            if len(frame) < start + 7:
                continue
            parsed = _parse_zone_body(frame[start : start + 10])
            if parsed is not None:
                return parsed
    return None, None


def resolve_internal_light(frames: list[bytes]) -> tuple[bool | None, ColorInfo | None]:
    zone = resolve_zone_chroma(frames)
    if zone.on is False:
        return False, None
    if zone.on is True:
        return True, zone.color
    return parse_zone_static_state(frames)


def resolve_brightness(
    primary_frames: list[bytes],
    extra_frames: list[bytes],
    *,
    header_req: int | None = None,
) -> int | None:
    value = parse_brightness(primary_frames, header_req=header_req)
    if value is not None:
        return value
    for frame in reversed(extra_frames):
        extra = parse_extra_brightness(frame)
        if extra is not None:
            return extra
    return None
