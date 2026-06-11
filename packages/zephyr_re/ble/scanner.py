"""BLE device discovery — advertising scan + macOS connected + known/session."""

from __future__ import annotations

import asyncio
import re
import subprocess
from dataclasses import dataclass, replace

from bleak import BleakScanner
from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData

from zephyr_re.settings import as_str, load_known_devices

LIVE_SOURCES = frozenset({"advertised", "resolved", "session", "retrieved"})
CONNECTABLE_SOURCES = frozenset(
    {"advertised", "resolved", "session", "retrieved", "system_connected"}
)


class DeviceNotAdvertisingError(ConnectionError):
    """Raised when the target peripheral is not visible on air (macOS)."""


@dataclass(frozen=True)
class BleDevice:
    address: str
    name: str | None
    rssi: int | None
    source: str = "advertised"
    bleak_device: BLEDevice | None = None

    @classmethod
    def from_bleak(
        cls,
        device: BLEDevice,
        adv: AdvertisementData | None = None,
        *,
        source: str = "advertised",
    ) -> BleDevice:
        rssi = adv.rssi if adv is not None else None
        name = as_str(device.name)
        if not name and adv is not None:
            name = as_str(adv.local_name)
        return cls(
            address=str(device.address),
            name=name,
            rssi=rssi,
            source=source,
            bleak_device=device,
        )

    @classmethod
    def from_known(cls, address: str, name: str | None, *, source: str = "known") -> BleDevice:
        return cls(address=address, name=name, rssi=None, source=source)

    def is_live(self) -> bool:
        """True if this entry was seen on-air during a recent scan."""
        return self.source in LIVE_SOURCES

    def is_connectable(self) -> bool:
        """True if the app can attempt a GATT session for this entry."""
        return self.source in CONNECTABLE_SOURCES


def _matches_patterns(name: str | None, patterns: list[str]) -> bool:
    if not name:
        return False
    lower = name.lower()
    return any(p.lower() in lower for p in patterns)


def _should_include(device: BleDevice, *, name_patterns: list[str] | None, show_all: bool) -> bool:
    if show_all:
        return True
    if not name_patterns:
        return True
    return _matches_patterns(device.name, name_patterns)


def _merge_device(existing: BleDevice | None, incoming: BleDevice) -> BleDevice:
    """Prefer entries with stronger signal / richer metadata."""
    if existing is None:
        return incoming
    bleak_device = incoming.bleak_device or existing.bleak_device
    if incoming.rssi is not None and (existing.rssi is None or incoming.rssi > existing.rssi):
        return replace(incoming, name=incoming.name or existing.name, bleak_device=bleak_device)
    if existing.name is None and incoming.name is not None:
        return replace(
            existing,
            name=incoming.name,
            source=incoming.source if incoming.source in LIVE_SOURCES else existing.source,
            bleak_device=bleak_device,
        )
    if incoming.bleak_device is not None and existing.bleak_device is None:
        return replace(existing, bleak_device=incoming.bleak_device, source=incoming.source)
    return existing


def parse_macos_connected_devices(
    name_patterns: list[str] | None = None,
    *,
    show_all: bool = False,
) -> list[BleDevice]:
    """Parse system_profiler for devices listed under the Connected section."""
    try:
        proc = subprocess.run(
            ["system_profiler", "SPBluetoothDataType"],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0 or not proc.stdout.strip():
        return []

    return _parse_macos_bluetooth_output(
        proc.stdout,
        name_patterns=name_patterns,
        show_all=show_all,
    )


def _parse_macos_bluetooth_output(
    text: str,
    *,
    name_patterns: list[str] | None,
    show_all: bool,
) -> list[BleDevice]:
    """Parse SPBluetoothDataType text (legacy flat list or Sequoia+ section layout)."""
    devices: list[BleDevice] = []
    current_name: str | None = None
    current_address: str | None = None
    connected = False
    in_connected_section = False
    use_section_format = False

    # Sequoia+: devices grouped under "Connected:" / "Not Connected:"
    section_connected = re.compile(r"^ {6}Connected:\s*$")
    section_not_connected = re.compile(r"^ {6}Not Connected:\s*$")
    device_header_new = re.compile(r"^ {10}([^:]+):\s*$")
    address_line_new = re.compile(r"^ {14}Address:\s+(.+)$", re.IGNORECASE)

    # Legacy: flat device entries with "Connected: Yes"
    device_header_old = re.compile(r"^ {4}([^:]+):\s*$")
    address_line_old = re.compile(r"^ {6}Address:\s+(.+)$", re.IGNORECASE)

    def flush() -> None:
        nonlocal current_name, current_address, connected
        if connected and current_address:
            dev = BleDevice(
                address=current_address.strip(),
                name=current_name,
                rssi=None,
                source="system_connected",
            )
            if _should_include(dev, name_patterns=name_patterns, show_all=show_all):
                devices.append(dev)
        current_name = None
        current_address = None
        connected = False

    for line in text.splitlines():
        if section_connected.match(line):
            use_section_format = True
            flush()
            in_connected_section = True
            continue
        if section_not_connected.match(line):
            flush()
            in_connected_section = False
            continue

        if use_section_format:
            header = device_header_new.match(line)
            if header:
                flush()
                current_name = header.group(1).strip()
                connected = in_connected_section
                continue
            addr = address_line_new.match(line)
            if addr:
                current_address = addr.group(1).strip()
                continue
            continue

        header = device_header_old.match(line)
        if header:
            flush()
            current_name = header.group(1).strip()
            continue
        addr = address_line_old.match(line)
        if addr:
            current_address = addr.group(1).strip()
            continue
        if line.strip() == "Connected: Yes":
            connected = True

    flush()
    return devices


async def resolve_device_by_address(
    address: str,
    *,
    timeout: float = 3.0,
) -> BleDevice | None:
    """Try to resolve a UUID/MAC via active scan (fresh peripheral handle)."""
    found = await BleakScanner.find_device_by_address(address, timeout=timeout)
    if found is not None:
        return BleDevice.from_bleak(found, source="resolved")
    return None


async def refresh_live_target(
    address: str,
    name_patterns: list[str] | None = None,
    *,
    quick_timeout: float = 4.0,
    full_scan_timeout: float = 12.0,
) -> BleDevice:
    """Re-find a device between connect retries — retrieve, scan, then system/known."""
    from zephyr_re.ble.macos_retrieve import resolve_macos_peripheral

    retrieved = await resolve_macos_peripheral(address, name_patterns=name_patterns)
    if retrieved is not None:
        return BleDevice.from_bleak(retrieved, source="retrieved")
    resolved = await resolve_device_by_address(address, timeout=quick_timeout)
    if resolved is not None:
        return resolved
    try:
        return await scan_for_zephyr(name_patterns, timeout=full_scan_timeout)
    except DeviceNotAdvertisingError:
        for candidate in _offline_zephyr_candidates(name_patterns):
            if candidate.address.lower() == address.lower():
                return candidate
        raise


def _offline_zephyr_candidates(name_patterns: list[str] | None) -> list[BleDevice]:
    """Paired Zephyr entries from System Settings and saved sessions."""
    patterns = list(name_patterns or ["Zephyr", "Razer", "Hazel"])
    merged: dict[str, BleDevice] = {}
    for dev in parse_macos_connected_devices(patterns):
        merged[dev.address] = dev
    for address, name in load_known_devices():
        if not _matches_patterns(name, patterns):
            continue
        merged.setdefault(address, BleDevice.from_known(address, name, source="known"))
    ordered = list(merged.values())
    ordered.sort(
        key=lambda d: (
            d.source != "system_connected",
            d.source != "known",
            d.name or "",
        )
    )
    return ordered


async def _scan_advertising(
    name_patterns: list[str] | None,
    *,
    timeout: float,
) -> dict[str, BleDevice]:
    patterns = list(name_patterns or ["Zephyr", "Razer", "Hazel"])
    candidates: dict[str, BleDevice] = {}

    def _callback(device: BLEDevice, adv: AdvertisementData) -> None:
        ble = BleDevice.from_bleak(device, adv, source="advertised")
        if _matches_patterns(ble.name, patterns):
            candidates[device.address] = _merge_device(candidates.get(device.address), ble)

    scanner = BleakScanner(detection_callback=_callback)
    await scanner.start()
    try:
        await asyncio.sleep(timeout)
    finally:
        await scanner.stop()
    return candidates


async def scan_for_zephyr(
    name_patterns: list[str] | None = None,
    *,
    timeout: float = 12.0,
) -> BleDevice:
    """Scan until a matching Zephyr/Razer mask is actively advertising."""
    candidates = await _scan_advertising(name_patterns, timeout=timeout)
    if not candidates:
        raise DeviceNotAdvertisingError(_not_found_message())
    return max(candidates.values(), key=lambda d: d.rssi or -999)


def _not_found_message() -> str:
    return (
        "Razer Zephyr not found.\n"
        "• Connect/pair in System Settings → Bluetooth, or put mask in pairing mode (blue blink)\n"
        "• Mask on, charged, within a metre of the Mac\n"
        "• Privacy & Security → Bluetooth → allow Terminal/Cursor\n"
        "• Then relaunch the app or use [6] Reconnect"
    )


async def find_zephyr_target(
    name_patterns: list[str] | None = None,
    *,
    scan_timeout: float = 4.0,
) -> BleDevice:
    """Find Zephyr for connect: advertising scan, then system-connected / known UUID."""
    from zephyr_re.ble.macos_retrieve import resolve_macos_peripheral

    patterns = list(name_patterns or ["Zephyr", "Razer", "Hazel"])
    advertised = await _scan_advertising(patterns, timeout=scan_timeout)
    if advertised:
        return max(advertised.values(), key=lambda d: d.rssi or -999)

    offline = _offline_zephyr_candidates(patterns)
    if not offline:
        raise DeviceNotAdvertisingError(_not_found_message())

    for candidate in offline:
        bleak_device = await resolve_macos_peripheral(
            candidate.address,
            name_patterns=patterns,
        )
        if bleak_device is not None:
            source = (
                "system_connected"
                if candidate.source == "system_connected"
                else "retrieved"
            )
            return BleDevice(
                address=candidate.address,
                name=candidate.name or as_str(bleak_device.name),
                rssi=None,
                source=source,
                bleak_device=bleak_device,
            )

    return offline[0]


async def scan_devices(
    timeout: float = 10.0,
    *,
    name_patterns: list[str] | None = None,
    show_all: bool = False,
    include_connected: bool = True,
    include_known: bool = True,
    session_device: BleDevice | None = None,
) -> list[BleDevice]:
    """Discover BLE devices from advertisements and optional metadata sources."""
    merged: dict[str, BleDevice] = {}

    def add(device: BleDevice) -> None:
        if not _should_include(device, name_patterns=name_patterns, show_all=show_all):
            return
        merged[device.address] = _merge_device(merged.get(device.address), device)

    def _callback(device: BLEDevice, adv: AdvertisementData) -> None:
        add(BleDevice.from_bleak(device, adv, source="advertised"))

    scanner = BleakScanner(detection_callback=_callback)
    await scanner.start()
    try:
        await asyncio.sleep(timeout)
    finally:
        await scanner.stop()

    if include_connected:
        for dev in parse_macos_connected_devices(name_patterns, show_all=show_all):
            add(dev)

    if include_known:
        for address, name in load_known_devices():
            add(BleDevice.from_known(address, name, source="known"))

    if session_device is not None:
        add(replace(session_device, source="session"))

    results = list(merged.values())
    results.sort(
        key=lambda d: (
            not d.is_live(),
            d.source != "session",
            d.source != "system_connected",
            d.rssi is None,
            -(d.rssi or -999),
            d.name or "",
        )
    )
    return results


def live_connect_candidates(
    scanned: list[BleDevice],
    *,
    name_patterns: list[str] | None = None,
) -> list[BleDevice]:
    """Devices the connect flow can use (advertising, system-connected, or retrieved)."""
    out: list[BleDevice] = []
    for dev in scanned:
        if not dev.is_connectable():
            continue
        if name_patterns and not _matches_patterns(dev.name, name_patterns):
            continue
        out.append(dev)
    return out


def discovery_candidates(
    scanned: list[BleDevice],
    *,
    session_device: BleDevice | None = None,
    name_patterns: list[str] | None = None,
    show_all: bool = False,
) -> list[BleDevice]:
    """Merge scan results for display (includes offline known entries)."""
    merged: dict[str, BleDevice] = {}
    for dev in scanned:
        if _should_include(dev, name_patterns=name_patterns, show_all=show_all):
            merged[dev.address] = dev
    if session_device is not None:
        add = replace(session_device, source="session")
        if _should_include(add, name_patterns=name_patterns, show_all=show_all):
            merged[add.address] = _merge_device(merged.get(add.address), add)
    for dev in parse_macos_connected_devices(name_patterns, show_all=show_all):
        merged[dev.address] = _merge_device(merged.get(dev.address), dev)
    results = list(merged.values())
    results.sort(
        key=lambda d: (
            not d.is_live(),
            d.source != "session",
            d.rssi is None,
            -(d.rssi or -999),
            d.name or "",
        )
    )
    return results
