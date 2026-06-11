"""Razer vendor GATT write exchange (header + payload → notify frames)."""

from __future__ import annotations

from zephyr_re.ble.client import BleClient
from zephyr_re.constants import (
    NOTIFY_TIMEOUT_MS,
    RAZER_VENDOR_NOTIFY,
    RAZER_VENDOR_NOTIFY_EXTRA,
    RAZER_VENDOR_WRITE,
    STATUS_SUCCESS,
)


def notify_uuids(client: BleClient) -> list[str]:
    uuids = [RAZER_VENDOR_NOTIFY]
    if client.find_characteristic(RAZER_VENDOR_NOTIFY_EXTRA) is not None:
        uuids.append(RAZER_VENDOR_NOTIFY_EXTRA)
    return uuids


def write_ack(frames: list[bytes]) -> bool:
    return any(len(frame) >= 8 and frame[7] == STATUS_SUCCESS for frame in frames)


async def send_vendor_writes(
    client: BleClient,
    writes: list[bytes],
    *,
    timeout_ms: int = NOTIFY_TIMEOUT_MS,
) -> tuple[list[bytes], bool]:
    """Send vendor packet(s); return notify frames and whether byte 7 was 0x02."""
    for uuid in notify_uuids(client):
        client.clear_notifications(uuid)
    for packet in writes:
        await client.write(RAZER_VENDOR_WRITE, packet, response=True)
    frames = await client.wait_for_notifications(
        RAZER_VENDOR_NOTIFY, timeout_ms, clear_first=False
    )
    for uuid in notify_uuids(client):
        if uuid.lower() != RAZER_VENDOR_NOTIFY.lower():
            frames.extend(client.drain_notifications(uuid))
    return frames, write_ack(frames)
