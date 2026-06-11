"""Read and decode every readable GATT characteristic."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

from zephyr_re.ble.client import BleClient, GattService
from zephyr_re.util.hexio import format_hex

# Well-known standard UUID suffixes (full UUIDs vary by stack formatting)
_STD_NAMES: dict[str, str] = {
    "00002a19": "Battery Level",
    "00002a29": "Manufacturer / Model Name",
    "00002a50": "PnP ID",
    "00002a24": "Model Number",
    "00002a25": "Serial Number",
    "00002a27": "Hardware Revision",
    "00002a26": "Firmware Revision",
    "00002a28": "Software Revision",
}


@dataclass
class GattReadResult:
    service_uuid: str
    char_uuid: str
    properties: list[str]
    data: bytes | None = None
    error: str | None = None
    hint: str | None = None

    @property
    def ok(self) -> bool:
        return self.data is not None and self.error is None


@dataclass
class NotifyCapture:
    char_uuid: str
    frames: list[bytes] = field(default_factory=list)


def _short_uuid(uuid: str) -> str:
    head = uuid.lower().split("-", 1)[0]
    if head.startswith("0000") and len(head) == 8:
        return head
    return uuid.lower()


def _decode_hint(char_uuid: str, data: bytes) -> str | None:
    short = _short_uuid(char_uuid)
    if short == "00002a19" and len(data) >= 1:
        pct = data[0]
        if pct > 100:
            pct = round(pct * 100 / 255)
        return f"Battery {pct}%"
    if short == "00002a29":
        try:
            text = data.decode("utf-8").strip("\x00")
            if text.isprintable() or text:
                return f"Text: {text!r}"
        except UnicodeDecodeError:
            pass
    if short == "00002a50" and len(data) >= 7:
        return (
            f"PnP vendor=0x{data[0]:02X}{data[1]:02X} "
            f"product=0x{data[2]:02X}{data[3]:02X}{data[4]:02X}{data[5]:02X} "
            f"version=0x{data[6]:02X}"
        )
    if "52401525" in char_uuid.lower() or "52401526" in char_uuid.lower():
        return f"Vendor payload ({len(data)} bytes)"
    return None


def _label(char_uuid: str) -> str:
    short = _short_uuid(char_uuid)
    return _STD_NAMES.get(short, short)


async def read_all_readable(client: BleClient, *, log_reads: bool = True) -> list[GattReadResult]:
    """Issue a GATT read on every characteristic that allows read."""
    results: list[GattReadResult] = []
    for svc in client.enumerate_gatt():
        for char in svc.characteristics:
            if "read" not in char.properties:
                continue
            result = GattReadResult(
                service_uuid=svc.uuid,
                char_uuid=char.uuid,
                properties=list(char.properties),
            )
            try:
                result.data = await client.read(char.uuid, log=log_reads)
                result.hint = _decode_hint(char.uuid, result.data)
            except Exception as exc:
                result.error = str(exc)
            results.append(result)
    return results


async def listen_notifications(
    client: BleClient,
    *,
    duration_s: float = 30.0,
    poll_interval_s: float = 0.25,
) -> list[NotifyCapture]:
    """Subscribe to all notify/indicate chars and collect traffic for duration_s."""
    subscribed = await client.subscribe_all_notifications()
    merged: dict[str, list[bytes]] = {uuid: [] for uuid in subscribed}
    deadline = asyncio.get_event_loop().time() + duration_s
    while asyncio.get_event_loop().time() < deadline:
        await asyncio.sleep(poll_interval_s)
        for uuid in subscribed:
            merged[uuid].extend(client.drain_notifications(uuid))
    return [
        NotifyCapture(char_uuid=uuid, frames=frames)
        for uuid, frames in merged.items()
        if frames
    ]


def format_read_results(results: list[GattReadResult]) -> list[str]:
    lines: list[str] = []
    for r in results:
        label = _label(r.char_uuid)
        if r.error:
            lines.append(f"[red]FAIL[/red] {label}")
            lines.append(f"  char {r.char_uuid}")
            lines.append(f"  {r.error}")
            continue
        assert r.data is not None
        lines.append(f"[green]OK[/green] {label}")
        lines.append(f"  char {r.char_uuid}")
        if r.hint:
            lines.append(f"  {r.hint}")
        lines.append(f"  hex  {format_hex(r.data)}")
        if len(r.data) <= 32:
            ascii_guess = "".join(chr(b) if 32 <= b < 127 else "." for b in r.data)
            if any(c != "." for c in ascii_guess):
                lines.append(f"  ascii {ascii_guess!r}")
    return lines
