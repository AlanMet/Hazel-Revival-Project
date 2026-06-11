"""Decode Razer Zephyr vendor notify frames (Hazel APK + hardware captures)."""

from __future__ import annotations

from dataclasses import dataclass

from zephyr_re.protocol.base import ColorInfo, FanSpeed

STATUS_OK = 0x02
STATUS_DATA = 0x07

# Legacy mouse-mode selector ids (10 03 00 00 u32)
EFFECT_ID_TO_NAME: dict[int, str] = {
    0: "static",
    1: "breathing",
    8: "spectrum",
}

# Hazel.java getEffectByZoneId — firmware effect type in continuation byte 0
HAZEL_EFFECT_BY_ID: dict[int, str] = {
    0: "off",
    1: "static",
    2: "breathing",
    3: "spectrum",
    4: "wave",
    7: "starlight",
}

# Hazel.zoneSupportedEffects — UI may expose more than firmware returns
EXTERNAL_ZONE_EFFECTS = frozenset({"static", "breathing", "spectrum", "wave"})
INTERNAL_ZONE_EFFECTS = frozenset({"static", "breathing", "spectrum"})

FAN_EXTRA_MAP: dict[int, FanSpeed] = {
    0: FanSpeed.OFF,
    1: FanSpeed.LOW,
    2: FanSpeed.HIGH,
}

DEFAULT_EFFECT = "spectrum"
ANIMATED_COLOR_NOTE = "No fixed color (animated effect)"

# 52401526 status prefix: 05 31 XX = brightness mirror, 05 39 XX = fan level
EXTRA_BRIGHTNESS_PREFIX = (0x05, 0x31)
EXTRA_FAN_PREFIX = (0x05, 0x39)

# Hazel.java zoneId = [5, 1] — external fan rings / internal mouth
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
    """True when payload is only the 12-byte session token (no RGB/effect data)."""
    return len(payload) == 12


def brightness_to_percent(value: int) -> int:
    """Map vendor brightness byte to 0–100% for display."""
    if value <= 100:
        return value
    return round(value * 100 / 255)


def parse_brightness(frames: list[bytes], *, header_req: int | None = None) -> int | None:
    """Brightness from 52401525 read reply; continuation frame byte 0 (0–255)."""
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
    """Brightness from 52401526 notify: 05 31 XX 00 00 08 00 00."""
    if len(frame) >= 3 and frame[0] == EXTRA_BRIGHTNESS_PREFIX[0] and frame[1] == EXTRA_BRIGHTNESS_PREFIX[1]:
        return frame[2]
    return None


def parse_extra_fan(frame: bytes) -> FanSpeed | None:
    """Fan level from 52401526 notify: 05 39 XX … (0=off, 1=low, 2=high)."""
    if len(frame) >= 3 and frame[0] == EXTRA_FAN_PREFIX[0] and frame[1] == EXTRA_FAN_PREFIX[1]:
        return FAN_EXTRA_MAP.get(frame[2])
    return None


def latest_fan_from_frames(frames: list[bytes]) -> FanSpeed | None:
    for frame in reversed(frames):
        speed = parse_extra_fan(frame)
        if speed is not None:
            return speed
    return None


def fan_from_extra_gatt(data: bytes) -> FanSpeed | None:
    """Fan level from 52401526 GATT read when mirror frame is present."""
    return parse_extra_fan(data)


def parse_fan_speed_read(frames: list[bytes]) -> FanSpeed | None:
    """Fan from Hazel createGetFanSpeed → continuation byte 2 (0/1/2)."""
    for frame in frames:
        if len(frame) >= 3 and frame[2] in FAN_EXTRA_MAP:
            return FAN_EXTRA_MAP[frame[2]]
    return None


def resolve_fan_speed(
    fan_read_frames: list[bytes],
    extra_frames: list[bytes],
    *,
    extra_gatt: bytes | None = None,
) -> tuple[FanSpeed, str]:
    speed = parse_fan_speed_read(fan_read_frames)
    if speed is not None:
        return speed, "read"
    if extra_gatt:
        speed = fan_from_extra_gatt(extra_gatt)
        if speed is not None:
            return speed, "extra_gatt"
    speed = latest_fan_from_frames(extra_frames)
    if speed is not None:
        return speed, "notify"
    return FanSpeed.OFF, "assumed"


def parse_firmware_version(frames: list[bytes]) -> str | None:
    """Firmware from Hazel createGetFirmwareVersion (00 81 00 00) — 4-byte version."""
    for frame in frames:
        if len(frame) >= 8 and frame[7] == STATUS_OK:
            tail = _payload_after_header(frame)
            if len(tail) >= 4 and not _is_device_token_only(tail):
                return _format_fw_bytes(tail[:4])
    # Continuation frame: version in bytes 0–3 (e.g. 01 00 09 00), not the req-id header.
    for frame in frames:
        if len(frame) >= 4 and frame[0] < 0x10 and all(b <= 99 for b in frame[:4]):
            return _format_fw_bytes(frame[:4])
    for frame in frames:
        if len(frame) >= 8 and frame[7] not in (STATUS_OK, STATUS_DATA):
            chunk = frame[:4]
            if all(b <= 99 for b in chunk):
                return _format_fw_bytes(chunk)
        if 4 <= len(frame) < 8:
            chunk = frame[:4]
            if all(b <= 99 for b in chunk):
                return _format_fw_bytes(chunk)
    return None


def _format_fw_bytes(chunk: bytes) -> str:
    return f"{chunk[0]:02d}.{chunk[1]:02d}.{chunk[2]:02d}.{chunk[3]:02d}"


def parse_charging_state(frames: list[bytes]) -> bool | None:
    """Charging flag from Hazel createGetChargingState (05 85 00 00)."""
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
    if effect_id == 7:
        return ZoneChromaState(effect=name, on=True, color_note="starlight")
    return ZoneChromaState(effect=name)


def parse_zone_chroma_effect(frames: list[bytes]) -> ZoneChromaState:
    """Parse Hazel per-zone chroma read (10 83 00 <zone>)."""
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
    """Chroma effect read, falling back to 10-byte zone on/off + RGB body."""
    chroma = parse_zone_chroma_effect(frames)
    if chroma.effect != "unknown":
        return chroma
    on, color = parse_zone_static_state(frames)
    if on is False:
        return ZoneChromaState(effect="off", on=False)
    if on is True or color is not None:
        return ZoneChromaState(effect="static", on=on, color=color)
    return ZoneChromaState()


def parse_color(frames: list[bytes]) -> tuple[ColorInfo | None, str | None]:
    """Parse external color; returns (color, note) when RGB is not fixed."""
    for frame in frames:
        if len(frame) < 12:
            continue
        status = frame[7]
        data = _payload_after_header(frame)
        if status == STATUS_OK:
            if len(data) >= 8 and data[0] == 0x04:
                return ColorInfo(r=data[5], g=data[6], b=data[7], raw=bytes(frame)), None
            if len(data) >= 4 and not _is_device_token_only(data):
                return ColorInfo(r=data[1], g=data[2], b=data[3], raw=bytes(frame)), None
        if status == STATUS_DATA and _is_device_token_only(data):
            return None, ANIMATED_COLOR_NOTE
    for frame in frames:
        if len(frame) >= 8 and frame[0] == 0x04:
            return ColorInfo(r=frame[5], g=frame[6], b=frame[7], raw=bytes(frame)), None
    if any(len(f) >= 8 and f[7] == STATUS_DATA for f in frames):
        return None, ANIMATED_COLOR_NOTE
    return None, None


def parse_effect(frames: list[bytes]) -> str | None:
    """Parse external lighting effect; defaults to spectrum when Zephyr returns 0x07 data."""
    if not frames:
        return None
    for frame in frames:
        if len(frame) < 8:
            continue
        status = frame[7]
        if status == STATUS_DATA:
            payload = _payload_after_header(frame)
            if _is_device_token_only(payload):
                return DEFAULT_EFFECT
        if status != STATUS_OK:
            continue
        effect_id = frame[1]
        if effect_id in EFFECT_ID_TO_NAME:
            return EFFECT_ID_TO_NAME[effect_id]
        tail = _payload_after_header(frame)
        if len(tail) >= 4 and not _is_device_token_only(tail):
            u32 = int.from_bytes(tail[:4], "little")
            if u32 in EFFECT_ID_TO_NAME:
                return EFFECT_ID_TO_NAME[u32]
    if any(len(f) >= 8 and f[7] == STATUS_DATA for f in frames):
        return DEFAULT_EFFECT
    return None


def is_vendor_response(frames: list[bytes]) -> bool:
    """True if any frame looks like a Zephyr vendor ack (0x02 or 0x07)."""
    return any(len(f) >= 8 and f[7] in (STATUS_OK, STATUS_DATA) for f in frames)


def _parse_zone_body(body: bytes) -> tuple[bool | None, ColorInfo | None] | None:
    """10-byte zone body: [on][marker×3][R][G][B]… — RGB at bytes 4–6."""
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
    """Per-zone static state from 10 83 00 <zone> (verified internal = zone 0x01)."""
    for frame in frames:
        if len(frame) >= 8 and frame[7] == STATUS_OK:
            parsed = _parse_zone_body(_payload_after_header(frame))
            if parsed is not None:
                return parsed
    # Continuation frame after OK header (byte 7 often 0x00, not 0x02)
    for frame in frames:
        for start in (0, 1):
            if len(frame) < start + 7:
                continue
            parsed = _parse_zone_body(frame[start : start + 10])
            if parsed is not None:
                return parsed
    for frame in frames:
        if len(frame) >= 8 and frame[0] == 0x04:
            return None, ColorInfo(r=frame[5], g=frame[6], b=frame[7], raw=bytes(frame))
    return None, None


def resolve_internal_light(frames: list[bytes]) -> tuple[bool | None, ColorInfo | None]:
    """Internal zone 0x01 — chroma effect read or static zone body."""
    zone = resolve_zone_chroma(frames)
    if zone.on is False:
        return False, None
    if zone.on is True:
        return True, zone.color
    on, color = parse_zone_static_state(frames)
    return on, color


def format_internal_light(
    on: bool | None,
    color: ColorInfo | None,
    *,
    zone: int | None = None,
) -> str:
    if on is False:
        return "off"
    display_color = color
    if on is True and display_color is None:
        display_color = DEFAULT_INTERNAL_GREEN
    if display_color is not None:
        hex_c = f"#{display_color.r:02X}{display_color.g:02X}{display_color.b:02X}"
        if on is True:
            is_default_green = (
                color is None
                and display_color.r == DEFAULT_INTERNAL_GREEN.r
                and display_color.g == DEFAULT_INTERNAL_GREEN.g
                and display_color.b == DEFAULT_INTERNAL_GREEN.b
            )
            suffix = " (green default)" if is_default_green else ""
            zone_bit = f", zone 0x{zone:02X}" if zone is not None else ""
            return f"on {hex_c}{suffix}{zone_bit}"
        return hex_c
    if on is True:
        return "on (green default #00FF00)"
    return "unknown"


def resolve_brightness(
    primary_frames: list[bytes],
    extra_frames: list[bytes],
    *,
    header_req: int | None = None,
) -> int | None:
    """Prefer 52401525 read reply; fall back to latest 52401526 05 31 XX."""
    value = parse_brightness(primary_frames, header_req=header_req)
    if value is not None:
        return value
    for frame in reversed(extra_frames):
        extra = parse_extra_brightness(frame)
        if extra is not None:
            return extra
    return None
