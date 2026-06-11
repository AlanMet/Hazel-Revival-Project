"""BLE transport for Razer Zephyr — connect and exchange vendor packets."""

from __future__ import annotations

from dataclasses import dataclass

from zephyr_re.ble.client import BleClient
from zephyr_re.ble.macos_retrieve import resolve_macos_peripheral
from zephyr_re.ble.null_capture import NullCapture
from zephyr_re.ble.scanner import BleDevice, find_zephyr_target, refresh_live_target
from zephyr_re.constants import (
    BATTERY_CHAR_UUID,
    RAZER_VENDOR_NOTIFY,
    RAZER_VENDOR_NOTIFY_EXTRA,
    RAZER_VENDOR_SERVICE,
    RAZER_VENDOR_WRITE,
)
from zephyr_re.protocol.vendor import send_vendor_writes
from zephyr_re.settings import as_str, device_name_patterns, save_known_device


@dataclass(frozen=True)
class ExchangeResult:
    frames: list[bytes]
    ack: bool


class ZephyrConnector:
    """Low-level Bluetooth connector: open GATT, send bytes, receive notifies."""

    def __init__(self) -> None:
        self._client: BleClient | None = None
        self._selected: BleDevice | None = None
        self._patterns = device_name_patterns()

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def address(self) -> str | None:
        return self._client.address if self._client else None

    @property
    def client(self) -> BleClient | None:
        return self._client

    @property
    def vendor_available(self) -> bool:
        if not self._client:
            return False
        return (
            self._client.find_service(RAZER_VENDOR_SERVICE) is not None
            and self._client.find_characteristic(RAZER_VENDOR_WRITE) is not None
            and self._client.find_characteristic(RAZER_VENDOR_NOTIFY) is not None
        )

    async def connect_foolproof(self, *, retries: int = 3) -> str:
        self._selected = await find_zephyr_target(self._patterns)
        return await self._connect_with_retries(self._selected.address, retries=retries)

    async def connect_to(self, device: BleDevice, *, retries: int = 3) -> str:
        """Connect to a specific scanned device."""
        self._selected = device
        return await self._connect_with_retries(device.address, retries=retries)

    async def _connect_with_retries(self, addr: str, *, retries: int) -> str:
        last_error: Exception | None = None
        device_name = as_str(self._selected.name) if self._selected else None
        for attempt in range(1, retries + 1):
            try:
                await self._connect_once(addr, attempt=attempt)
                save_known_device(addr, device_name or (self._client.device_name if self._client else None))
                return addr
            except Exception as exc:
                last_error = exc
                if self._client and self._client.is_connected:
                    await self.disconnect()
                if attempt < retries:
                    import asyncio

                    await asyncio.sleep(1.5)
                    self._selected = await refresh_live_target(addr, self._patterns)
                    addr = self._selected.address
                    device_name = as_str(self._selected.name) or device_name
        assert last_error is not None
        raise last_error

    async def _connect_once(self, addr: str, *, attempt: int) -> None:
        bleak_device = (
            self._selected.bleak_device
            if self._selected and self._selected.bleak_device is not None
            else None
        )
        if bleak_device is None:
            bleak_device = await resolve_macos_peripheral(addr, name_patterns=self._patterns)
        capture = NullCapture()
        if bleak_device is not None:
            self._client = BleClient(bleak_device, capture=capture)
        else:
            self._client = BleClient(addr, capture=capture)
        await self._client.connect()
        await self._client.subscribe_uuids(
            [RAZER_VENDOR_NOTIFY, RAZER_VENDOR_NOTIFY_EXTRA, BATTERY_CHAR_UUID]
        )

    async def disconnect(self) -> None:
        if self._client:
            await self._client.disconnect()
        self._client = None

    async def send(self, packets: list[bytes], *, timeout_ms: int = 1500) -> ExchangeResult:
        if not self._client:
            raise RuntimeError("Not connected")
        frames, ack = await send_vendor_writes(self._client, packets, timeout_ms=timeout_ms)
        return ExchangeResult(frames=frames, ack=ack)
