"""Hazel APK write packet builders (ChromaFirmwareEffectFactoryProtocol3 + Hazel.java)."""

from __future__ import annotations

from dataclasses import dataclass

from zephyr_re.protocol.base import FanSpeed
from zephyr_re.constants import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE

# Hazel.java FanSpeedSettings.value
FAN_LEVEL: dict[FanSpeed, int] = {
    FanSpeed.OFF: 0,
    FanSpeed.LOW: 1,
    FanSpeed.HIGH: 2,
}

# Firmware wire byte 0 in effect payload (NOT the same as EffectType enum IDs in the app).
# APK writers only use 0–4 and 7; 5/6/8+ are unverified on Zephyr hardware.
FIRMWARE_EFFECT_WIRE: dict[int, str] = {
    0: "off",
    1: "static",
    2: "breathing",
    3: "spectrum",
    4: "wave",
    5: "unknown (app EffectType.WaveDynamic=5 — phone-side, not sent to firmware)",
    6: "unknown (app EffectType.AudioReactive=6)",
    7: "starlight",
    8: "unknown (app EffectType.Starlight=8 — enum id ≠ wire id)",
    9: "unknown (app EffectType.Breathing2=9)",
    10: "unknown (app EffectType.BreathingWithFirmare=10)",
}

EFFECT_TYPE: dict[str, int] = {
    "off": 0,
    "static": 1,
    "breathing": 2,
    "spectrum": 3,
    "wave": 4,
    "starlight": 7,
}

# Wave payload byte 2 — higher = slower rotation (factory read 0x5A on zone 0x05).
WAVE_RATE_FACTORY = 90  # 0x5A — device default before Hazel probe writes
WAVE_RATE_SLOW = 15  # APK: app rate 0
WAVE_RATE_MEDIUM = 50  # APK: app rate 100 (Hazel createWaveStatic default)
WAVE_RATE_FAST = 100  # APK: app rate 255

WAVE_SPEED_PRESETS: dict[str, int] = {
    "factory": WAVE_RATE_FACTORY,
    "slow": WAVE_RATE_SLOW,
    "medium": WAVE_RATE_MEDIUM,
    "fast": WAVE_RATE_FAST,
}


def wave_ble_rate_from_app_rate(app_rate: int) -> int:
    """Map Hazel Wave.rate (UI uses 255 - rate) to firmware byte per APK."""
    if app_rate == 255:
        return WAVE_RATE_FAST
    if app_rate == 0:
        return WAVE_RATE_SLOW
    return WAVE_RATE_MEDIUM


def zone_effect_read_header(req_id: int, zone: int) -> bytes:
    """Read zone chroma/effect — key 10 83 00 <zone>."""
    return bytes([req_id & 0xFF, 0x00, 0x00, 0x00, 0x10, 0x83, 0x00, zone & 0xFF])


def effect_id_probe_packets(req_id: int, effect_id: int, zone: int) -> tuple[bytes, bytes]:
    """Hazel effect write for discovery sweeps (sensible defaults per wire ID)."""
    if effect_id == 0:
        return effect_off_v3_packets(req_id, zone)
    if effect_id == 1:
        # Bare `01 00 00 00` is rejected (0x03); static needs RGB per APK.
        if zone == INTERNAL_LIGHT_ZONE:
            return effect_packets(req_id, "static", zone, r=0, g=255, b=0)
        return effect_packets(req_id, "static", zone, r=255, g=0, b=0)
    if effect_id == 4:
        return effect_packets(req_id, "wave", zone, wave_rate=WAVE_RATE_FACTORY)
    if effect_id == 7:
        payload = ble_effect_configuration(7, 1, 1)
        return effect_set_header(req_id, payload, zone=zone), payload
    payload = ble_effect_configuration(effect_id, 0, 0)
    return effect_set_header(req_id, payload, zone=zone), payload


def effect_set_header(req_id: int, payload: bytes, *, sub_id: int = 0, zone: int) -> bytes:
    """ChromaProtocolHelperBackpack.createBluetoothStaticSetEffectHeader."""
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
    """ChromaFirmwareEffectFactoryProtocol3.createBleEffectrConfiguration."""
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
    """ChromaProtocolHelper.createBluetoothOffEffectv3 — payload is single 0x00."""
    payload = b"\x00"
    return effect_set_header(req_id, payload, sub_id=sub_id, zone=zone), payload


def effect_off_packets(
    req_id: int,
    zone: int,
    *,
    sub_id: int = 0,
) -> tuple[bytes, bytes]:
    """createOffEffect via applyFirmwareEffect — payload 00 00 00 00."""
    payload = ble_effect_configuration(0, 0, 0)
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
    """Two-packet zone effect write (applyFirmwareEffect path)."""
    name = effect.lower()
    effect_type = EFFECT_TYPE.get(name)
    if effect_type is None:
        raise ValueError(f"Unknown Hazel effect: {effect}")

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
    elif effect_type == 7:
        payload = ble_effect_configuration(7, 1, 1)
    else:
        raise ValueError(f"Unsupported Hazel effect type: {effect_type}")

    return effect_set_header(req_id, payload, sub_id=sub_id, zone=zone), payload


def static_color_packets(
    req_id: int,
    r: int,
    g: int,
    b: int,
    zone: int = EXTERNAL_LIGHT_ZONE,
    *,
    sub_id: int = 0,
) -> tuple[bytes, bytes]:
    return effect_packets(req_id, "static", zone, sub_id=sub_id, r=r, g=g, b=b)


# Hazel.java createSetTimeoutCommand — auto-off minutes (OPUS_* TimeoutSettings.value)
HAZEL_TIMEOUT_MINUTES: dict[str, int] = {
    "never": 0,
    "5min": 5,
    "15min": 15,
    "30min": 30,
    "45min": 45,
    "60min": 60,
}


def hazel_timeout_set_packet(minutes_code: int) -> bytes:
    """Hazel createSetTimeoutCommand — 4 bytes, no transaction id prefix."""
    return bytes([0xA7, 0x00, 0x01, minutes_code & 0xFF])


def hazel_timeout_get_packet() -> bytes:
    """Hazel createGetTimeoutCommand — 3 bytes; reply byte 3 = current setting."""
    return bytes([0x27, 0x00, 0x00])


def firmware_read_header(req_id: int) -> bytes:
    """Hazel createGetFirmwareVersion — 00 81 00 00."""
    return bytes([req_id & 0xFF, 0x00, 0x00, 0x00, 0x00, 0x81, 0x00, 0x00])


def chroma_timeout_packet(req_id: int, seconds: int) -> bytes:
    """ChromaProtocolHelper.createBlueoothSetTimeout(s,s,s) — seconds via (s << 8) encoding."""
    packed = (max(0, min(0xFFFF, seconds)) & 0xFFFF) << 8
    mid = (packed >> 8) & 0xFF
    hi = (packed >> 16) & 0xFF
    return bytes(
        [req_id & 0xFF, 0x06, 0x00, 0x00, 0x01, 0x0B, 0x00, 0x00, mid, hi, mid, hi, mid, hi]
    )


def starlight_packets(
    req_id: int,
    zone: int,
    *,
    rate: int = 2,
    r: int | None = None,
    g: int | None = None,
    b: int | None = None,
    r2: int | None = None,
    g2: int | None = None,
    b2: int | None = None,
) -> tuple[bytes, bytes]:
    """Wire ID 7 — random LED sparkles; optional 1–2 anchor colors (APK Starlight)."""
    c1 = (r & 0xFF, g & 0xFF, b & 0xFF) if r is not None and g is not None and b is not None else None
    c2 = None
    if r2 is not None and g2 is not None and b2 is not None:
        c2 = (r2 & 0xFF, g2 & 0xFF, b2 & 0xFF)
    payload = ble_effect_configuration(7, 1, rate & 0xFF, color1=c1, color2=c2)
    return effect_set_header(req_id, payload, zone=zone), payload


def brightness_packets(req_id: int, brightness: int, zone: int) -> tuple[bytes, bytes]:
    """ChromaFirmwareEffectFactoryProtocol3.createBleSetBrightness(0, level, zone)."""
    level = max(0, min(255, brightness))
    header = bytes([req_id & 0xFF, 0x01, 0x00, 0x00, 0x10, 0x05, 0x00, zone & 0xFF])
    return header, bytes([level])


def fan_speed_packets(req_id: int, speed: FanSpeed) -> tuple[bytes, bytes]:
    """Hazel.createSetFanSpeed — firmware >= 01.00.00.01 layout."""
    level = FAN_LEVEL[speed]
    header = bytes([req_id & 0xFF, 0x06, 0x00, 0x00, 0x11, 0x01, 0x01, 0x00])
    payload = bytes([0x01, 0x00, level & 0xFF, 0x00, level & 0xFF, 0x00])
    return header, payload


def internal_light_packets(
    req_id: int,
    on: bool,
    r: int = 0,
    g: int = 0,
    b: int = 0,
) -> tuple[bytes, bytes]:
    if not on:
        return effect_off_v3_packets(req_id, INTERNAL_LIGHT_ZONE)
    if on and r == 0 and g == 0 and b == 0:
        r, g, b = 0, 255, 0
    return static_color_packets(req_id, r, g, b, INTERNAL_LIGHT_ZONE)


@dataclass(frozen=True)
class HazelWritePair:
    """Two-packet vendor write (header + payload) with a human label."""

    name: str
    header: bytes
    payload: bytes

    @property
    def writes(self) -> list[bytes]:
        return [self.header, self.payload]


def reference_write_pairs(req_start: int = 0x30) -> list[HazelWritePair]:
    """Hazel APK reference writes — effects first (restore after static color)."""
    req = req_start
    ext = EXTERNAL_LIGHT_ZONE
    intr = INTERNAL_LIGHT_ZONE
    pairs: list[HazelWritePair] = []

    def add(name: str, header: bytes, payload: bytes) -> None:
        pairs.append(HazelWritePair(name, header, payload))

    # External effects — wave = rotating ring (factory default); spectrum = gradient
    h, p = effect_packets(req, "wave", ext, wave_rate=WAVE_RATE_FACTORY)
    add(f"wave zone 0x{ext:02X} (rotating ring, rate {WAVE_RATE_FACTORY})", h, p)
    req += 1
    h, p = effect_packets(req, "spectrum", ext)
    add(f"spectrum zone 0x{ext:02X} (gradient cycle)", h, p)
    req += 1
    h, p = effect_packets(req, "breathing", ext)
    add(f"breathing zone 0x{ext:02X}", h, p)
    req += 1
    h, p = effect_off_v3_packets(req, ext)
    add(f"external off zone 0x{ext:02X}", h, p)
    req += 1
    h, p = static_color_packets(req, 0xFF, 0x00, 0x00, ext)
    add(f"static #FF0000 zone 0x{ext:02X}", h, p)
    req += 1
    h, p = brightness_packets(req, 128, ext)
    add(f"brightness 128 zone 0x{ext:02X}", h, p)
    req += 1
    # Internal mouth zone
    h, p = static_color_packets(req, 0x00, 0xFF, 0x00, intr)
    add(f"static #00FF00 zone 0x{intr:02X} (internal)", h, p)
    req += 1
    h, p = effect_off_v3_packets(req, intr)
    add(f"internal off zone 0x{intr:02X}", h, p)
    req += 1
    # Fans
    h, p = fan_speed_packets(req, FanSpeed.HIGH)
    add("fan high", h, p)
    req += 1
    h, p = fan_speed_packets(req, FanSpeed.LOW)
    add("fan low", h, p)
    req += 1
    h, p = fan_speed_packets(req, FanSpeed.OFF)
    add("fan off", h, p)
    return pairs
