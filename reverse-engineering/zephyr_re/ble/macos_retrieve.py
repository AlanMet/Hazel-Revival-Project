"""Resolve paired / system-connected BLE peripherals without an active advertisement."""

from __future__ import annotations

import sys

from bleak.backends.device import BLEDevice

from zephyr_re.settings import as_str

RAZER_VENDOR_SERVICE = "52401523-F97C-7F90-0E7F-6C6F4E36DB1C"
BATTERY_SERVICE = "0000180f-0000-1000-8000-00805f9b34fb"


def _matches_patterns(name: str | None, patterns: list[str]) -> bool:
    if not name:
        return False
    lower = name.lower()
    return any(p.lower() in lower for p in patterns)


async def resolve_macos_peripheral(
    address: str,
    *,
    name_patterns: list[str] | None = None,
) -> BLEDevice | None:
    """Find a peripheral by UUID or among system-connected GATT devices (macOS)."""
    if sys.platform != "darwin":
        return None

    from CoreBluetooth import CBUUID
    from Foundation import NSArray, NSUUID
    from bleak.backends.corebluetooth.CentralManagerDelegate import CentralManagerDelegate

    patterns = list(name_patterns or ["Zephyr", "Razer", "Hazel"])
    uuid_str = address.strip().upper()
    manager = CentralManagerDelegate()
    await manager.wait_until_ready()
    central = manager.central_manager

    ns_uuid = NSUUID.alloc().initWithUUIDString_(uuid_str)
    if ns_uuid is not None:
        peripherals = central.retrievePeripheralsWithIdentifiers_(
            NSArray.arrayWithObject_(ns_uuid)
        )
        if peripherals and len(peripherals) > 0:
            peripheral = peripherals[0]
            return BLEDevice(
                peripheral.identifier().UUIDString(),
                as_str(peripheral.name()),
                (peripheral, manager),
            )

    service_ids = NSArray.arrayWithArray_(
        [
            CBUUID.UUIDWithString_(RAZER_VENDOR_SERVICE),
            CBUUID.UUIDWithString_(BATTERY_SERVICE),
        ]
    )
    connected = central.retrieveConnectedPeripheralsWithServices_(service_ids)
    if not connected:
        return None

    for peripheral in connected:
        pid = peripheral.identifier().UUIDString().upper()
        name = as_str(peripheral.name())
        if pid == uuid_str:
            return BLEDevice(pid, name, (peripheral, manager))
        if _matches_patterns(name, patterns):
            return BLEDevice(pid, name, (peripheral, manager))

    if len(connected) == 1:
        peripheral = connected[0]
        return BLEDevice(
            peripheral.identifier().UUIDString(),
            as_str(peripheral.name()),
            (peripheral, manager),
        )

    return None
