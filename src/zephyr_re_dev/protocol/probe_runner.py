"""Try curated vendor-write variants until the mask acks or candidates are exhausted."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any

import yaml

from zephyr_re.ble.client import BleClient
from zephyr_re.protocol.vendor import send_vendor_writes, write_ack as vendor_write_ack
from zephyr_re_dev.config import project_root
from zephyr_re.protocol.base import CommandResult, CommandStatus
from zephyr_re_dev.protocol.hazel_write import (
    FIRMWARE_EFFECT_WIRE,
    brightness_packets,
    chroma_timeout_packet,
    effect_id_probe_packets,
    effect_packets,
    firmware_read_header,
    hazel_timeout_get_packet,
    hazel_timeout_set_packet,
    starlight_packets,
    zone_effect_read_header,
)
from zephyr_re_dev.protocol.zephyr_parse import (
    EXTERNAL_LIGHT_ZONE,
    INTERNAL_LIGHT_ZONE,
    parse_firmware_version,
)
from zephyr_re.constants import (
    NOTIFY_TIMEOUT_MS,
    RAZER_VENDOR_NOTIFY,
    RAZER_VENDOR_NOTIFY_EXTRA,
    STATUS_SUCCESS,
)
from zephyr_re_dev.protocol.zephyr_parse import parse_zone_chroma_effect
from zephyr_re_dev.util.frame_decode import decode_vendor_frame
from zephyr_re.util.hexio import format_hex, parse_hex

PROBE_PATH = project_root() / "tools" / "config" / "probe_candidates.yaml"


@dataclass(frozen=True)
class ProbeAttempt:
    name: str
    writes: list[bytes]
    frames: list[bytes]

    @property
    def ack(self) -> bool:
        for frame in self.frames:
            if len(frame) >= 8 and frame[7] == STATUS_SUCCESS:
                return True
        return False

    @property
    def any_reply(self) -> bool:
        return bool(self.frames)


def _probe_candidates_path() -> Path:
    return PROBE_PATH


def load_probe_lists() -> dict[str, list[dict[str, Any]]]:
    path = _probe_candidates_path()
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: dict[str, list[dict[str, Any]]] = {}
    for key, entries in raw.items():
        if isinstance(entries, list):
            out[key] = [e for e in entries if isinstance(e, dict)]
    return out


def _format_writes(
    templates: list[str],
    *,
    req_id: int,
    fmt: dict[str, Any],
) -> list[bytes]:
    values = {"req": req_id, **fmt}
    return [parse_hex(t.format(**values)) for t in templates]


async def run_probe_list(
    client: BleClient,
    list_name: str,
    *,
    fmt: dict[str, Any],
    req_id_start: int = 0x30,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> list[ProbeAttempt]:
    entries = load_probe_lists().get(list_name, [])
    attempts: list[ProbeAttempt] = []
    req_id = req_id_start
    total = sum(
        1
        for entry in entries
        if isinstance(entry.get("writes"), list) and entry.get("writes")
    )
    index = 0
    for entry in entries:
        name = str(entry.get("name") or f"candidate_{len(attempts)}")
        templates = entry.get("writes") or []
        if not isinstance(templates, list) or not templates:
            continue
        index += 1
        writes = _format_writes([str(t) for t in templates], req_id=req_id, fmt=fmt)
        client.capture.log_section(f"probe:{list_name} {name} [{index}/{total}]")
        frames = await _vendor_exchange_writes(client, writes)
        attempt = ProbeAttempt(name=name, writes=writes, frames=frames)
        attempts.append(attempt)
        if attempt.ack:
            result = "ACK"
        elif attempt.any_reply:
            result = "reply"
        else:
            result = "silent"
        detail = None
        if frames:
            detail = decode_vendor_frame(frames[0])
            if len(frames) > 1:
                detail += f"; +{len(frames) - 1} more"
        client.capture.log_operation(
            name,
            index=index,
            total=total,
            result=result,
            writes=writes,
            frames=frames,
            detail=detail,
        )
        if on_attempt is not None:
            on_attempt(attempt, index, total)
        req_id = (req_id + 1) & 0xFF
    return attempts


def _best_attempt(attempts: list[ProbeAttempt]) -> ProbeAttempt | None:
    for attempt in attempts:
        if attempt.ack:
            return attempt
    for attempt in attempts:
        if attempt.any_reply:
            return attempt
    return None


def _result_from_attempts(
    attempts: list[ProbeAttempt],
    *,
    label: str,
    empty_message: str,
) -> CommandResult:
    if not attempts:
        return CommandResult(CommandStatus.NOT_CONFIGURED, empty_message)
    best = _best_attempt(attempts)
    if best and best.ack:
        hex_writes = " | ".join(format_hex(w) for w in best.writes)
        return CommandResult(
            CommandStatus.OK,
            f"{label}: mask acked {best.name} — {hex_writes}",
            best.frames,
        )
    if best and best.any_reply:
        hex_reply = "; ".join(format_hex(f) for f in best.frames[:2])
        return CommandResult(
            CommandStatus.PARTIAL,
            f"{label}: {best.name} got a reply (unverified): {hex_reply}",
            best.frames,
        )
    tried = ", ".join(a.name for a in attempts)
    return CommandResult(
        CommandStatus.PARTIAL,
        f"{label}: no ack from {len(attempts)} patterns ({tried})",
        attempts[-1].frames if attempts else None,
    )


async def probe_external_color(
    client: BleClient,
    r: int,
    g: int,
    b: int,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await run_probe_list(
        client,
        "external_color",
        fmt={"r": r & 0xFF, "g": g & 0xFF, "b": b & 0xFF},
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label="Color probe",
        empty_message="No probe candidates in tools/config/probe_candidates.yaml",
    )


async def probe_vendor_reads(
    client: BleClient,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> list[ProbeAttempt]:
    """Send curated vendor READ keys and return all attempts (for discovery)."""
    return await run_probe_list(client, "vendor_reads", fmt={}, on_attempt=on_attempt)


async def probe_external_effect_static(
    client: BleClient,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await run_probe_list(
        client,
        "external_effect_static",
        fmt={"effect": 0},
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label="Static effect probe",
        empty_message="No effect probe candidates in tools/config/probe_candidates.yaml",
    )


async def probe_external_static_then_color(
    client: BleClient,
    r: int,
    g: int,
    b: int,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await run_probe_list(
        client,
        "external_static_then_color",
        fmt={"r": r & 0xFF, "g": g & 0xFF, "b": b & 0xFF},
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label="Static-then-color probe",
        empty_message="No static-then-color candidates in tools/config/probe_candidates.yaml",
    )


async def probe_internal_light(
    client: BleClient,
    r: int,
    g: int,
    b: int,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await run_probe_list(
        client,
        "internal_light",
        fmt={"r": r & 0xFF, "g": g & 0xFF, "b": b & 0xFF},
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label="Internal light probe",
        empty_message="No internal_light candidates in tools/config/probe_candidates.yaml",
    )


async def probe_firmware_effect_id_sweep(
    client: BleClient,
    zone: int,
    *,
    id_start: int = 0,
    id_end: int = 15,
    req_id_start: int = 0x40,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> list[ProbeAttempt]:
    """Try firmware effect wire IDs id_start..id_end on a zone; read back chroma after each write."""
    attempts: list[ProbeAttempt] = []
    total = id_end - id_start + 1
    for i, effect_id in enumerate(range(id_start, id_end + 1)):
        req = req_id_start + i
        header, payload = effect_id_probe_packets(req, effect_id, zone)
        frames, ack = await send_vendor_writes(client, [header, payload])
        read_note = ""
        read_frames = await _vendor_exchange_writes(
            client,
            [zone_effect_read_header(req + 0x20, zone)],
            timeout_ms=NOTIFY_TIMEOUT_MS,
        )
        read_body_id: int | None = None
        if read_frames:
            parsed = parse_zone_chroma_effect(read_frames)
            for frame in read_frames:
                if len(frame) >= 8 and frame[7] == STATUS_SUCCESS:
                    tail = frame[8:]
                    if tail and tail[0] in range(16):
                        read_body_id = tail[0]
                        break
            applied = ack and read_body_id == effect_id
            read_note = f" ack={'yes' if ack else 'no'} applied={'yes' if applied else 'no'}"
            if read_body_id is not None:
                read_note += f" read_body=0x{read_body_id:02X}({parsed.effect})"
        else:
            read_note = f" ack={'yes' if ack else 'no'} applied=?"
        apk_hint = FIRMWARE_EFFECT_WIRE.get(effect_id, "unknown")
        name = f"wire_id_{effect_id:02d}_zone_{zone:02X}{read_note} ({apk_hint})"
        attempt = ProbeAttempt(name, [header, payload], frames)
        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt, i + 1, total)
        if not ack:
            pass  # still continue sweep
    return attempts


async def probe_firmware_effect_id_sweep_result(
    client: BleClient,
    zone: int,
    *,
    id_start: int = 0,
    id_end: int = 15,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await probe_firmware_effect_id_sweep(
        client,
        zone,
        id_start=id_start,
        id_end=id_end,
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label=f"Firmware effect ID sweep zone 0x{zone:02X}",
        empty_message="No effect IDs in range",
    )


async def _run_probe_writes(
    client: BleClient,
    specs: list[tuple[str, list[bytes]]],
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> list[ProbeAttempt]:
    attempts: list[ProbeAttempt] = []
    total = len(specs)
    for i, (name, writes) in enumerate(specs, 1):
        frames, _ack = await send_vendor_writes(client, writes)
        attempt = ProbeAttempt(name, writes, frames)
        attempts.append(attempt)
        if on_attempt:
            on_attempt(attempt, i, total)
    return attempts


HAZEL_TIMEOUT_TEST_SECONDS = 30


async def restore_hazel_led_timeout(
    client: BleClient,
    *,
    req_id: int = 0x70,
) -> tuple[list[bytes], bool]:
    """Set Hazel LED auto-off to never (A7) and clear chroma timeout (0B) if supported."""
    frames: list[bytes] = []
    ack = False
    for packet in (hazel_timeout_set_packet(0), chroma_timeout_packet(req_id, 0)):
        part, part_ack = await send_vendor_writes(client, [packet])
        frames.extend(part)
        ack = ack or part_ack
    return frames, ack


async def restore_hazel_led_timeout_result(client: BleClient) -> CommandResult:
    frames, ack = await restore_hazel_led_timeout(client)
    status = CommandStatus.OK if ack else CommandStatus.ERROR
    return CommandResult(
        status,
        "Restore LED timeout (never)" if ack else "Restore LED timeout — no ACK",
        responses=frames,
    )


async def probe_hazel_extras(
    client: BleClient,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> list[ProbeAttempt]:
    """Brightness, breathing, starlight, firmware read, LED timeout probes — APK-derived."""
    req = 0x50
    specs: list[tuple[str, list[bytes]]] = []

    def add(name: str, header: bytes, payload: bytes | None = None) -> None:
        nonlocal req
        if payload is None:
            specs.append((name, [header]))
        else:
            specs.append((name, [header, payload]))
        req += 1

    specs.append(("firmware_read", [firmware_read_header(req)]))
    req += 1

    for zone, label in ((EXTERNAL_LIGHT_ZONE, "ext"), (INTERNAL_LIGHT_ZONE, "int")):
        for level in (64, 128, 255):
            h, p = brightness_packets(req, level, zone)
            add(f"brightness_{label}_0x{zone:02X}_{level}", h, p)

    ext = EXTERNAL_LIGHT_ZONE
    h, p = effect_packets(req, "breathing", ext)
    add("breathing_ext_default", h, p)
    h, p = effect_packets(req, "breathing", ext, r=255, g=0, b=0)
    add("breathing_ext_red", h, p)
    h, p = effect_packets(req, "breathing", ext, r=255, g=0, b=0, r2=0, g2=0, b2=255)
    add("breathing_ext_red_blue", h, p)

    for rate, rate_name in ((1, "slow"), (2, "medium"), (3, "fast")):
        h, p = starlight_packets(req, ext, rate=rate)
        add(f"starlight_ext_{rate_name}_random", h, p)
    h, p = starlight_packets(req, ext, rate=2, r=255, g=0, b=0)
    add("starlight_ext_red_sparkle", h, p)
    h, p = starlight_packets(req, ext, rate=2, r=255, g=0, b=0, r2=0, g2=255, b2=0)
    add("starlight_ext_red_green", h, p)

    specs.append(("timeout_get", [hazel_timeout_get_packet()]))
    specs.append(
        (
            f"timeout_set_chroma_{HAZEL_TIMEOUT_TEST_SECONDS}s",
            [chroma_timeout_packet(req, HAZEL_TIMEOUT_TEST_SECONDS)],
        )
    )
    req += 1
    specs.append(
        (
            f"timeout_set_hazel_raw_{HAZEL_TIMEOUT_TEST_SECONDS}",
            [hazel_timeout_set_packet(HAZEL_TIMEOUT_TEST_SECONDS)],
        )
    )

    attempts = await _run_probe_writes(client, specs, on_attempt=on_attempt)
    for i, attempt in enumerate(attempts):
        if attempt.name == "firmware_read" and attempt.frames:
            version = parse_firmware_version(attempt.frames)
            if version:
                attempts[i] = ProbeAttempt(
                    name=f"firmware_read ({version})",
                    writes=attempt.writes,
                    frames=attempt.frames,
                )
    return attempts


async def probe_hazel_extras_result(
    client: BleClient,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await probe_hazel_extras(client, on_attempt=on_attempt)
    if not attempts:
        return CommandResult(CommandStatus.NOT_CONFIGURED, "No Hazel extra probes configured")
    ack_n = sum(1 for a in attempts if a.ack)
    rej_n = sum(
        1
        for a in attempts
        if a.any_reply and not a.ack and any(len(f) >= 8 and f[7] == 0x03 for f in a.frames)
    )
    summary = (
        f"Hazel extras: {ack_n}/{len(attempts)} ACK — "
        f"brightness/breathing OK; starlight+timeout rejected ({rej_n}×0x03) on this firmware"
    )
    return CommandResult(CommandStatus.PARTIAL if rej_n else CommandStatus.OK, summary, attempts[-1].frames)


async def probe_fan_speed(
    client: BleClient,
    fan: int,
    *,
    on_attempt: Callable[[ProbeAttempt, int, int], None] | None = None,
) -> CommandResult:
    attempts = await run_probe_list(
        client,
        "fan_speed",
        fmt={"fan": fan & 0xFF},
        on_attempt=on_attempt,
    )
    return _result_from_attempts(
        attempts,
        label="Fan speed probe",
        empty_message="No fan_speed candidates in tools/config/probe_candidates.yaml",
    )
