"""BLE GATT client wrapper with capture logging and serialized writes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Callable

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.backends.service import BleakGATTService

from zephyr_re.ble.null_capture import NullCapture

DEFAULT_GATT_TIMEOUT_S = 8.0

CaptureLog = NullCapture  # type alias; dev package replaces with GattCaptureLog


class GattOperationTimeout(TimeoutError):
    """BLE read/write did not complete within the allotted time."""


@dataclass(frozen=True)
class GattCharacteristic:
    uuid: str
    handle: int
    properties: list[str]
    service_uuid: str

    @classmethod
    def from_bleak(cls, char: BleakGATTCharacteristic, service_uuid: str) -> GattCharacteristic:
        props: list[str] = []
        if "read" in char.properties:
            props.append("read")
        if "write" in char.properties or "write-without-response" in char.properties:
            props.append("write")
        if "notify" in char.properties:
            props.append("notify")
        if "indicate" in char.properties:
            props.append("indicate")
        return cls(
            uuid=char.uuid,
            handle=char.handle,
            properties=props,
            service_uuid=service_uuid,
        )


@dataclass(frozen=True)
class GattService:
    uuid: str
    characteristics: list[GattCharacteristic]


class BleClient:
    """Thin async wrapper around BleakClient."""

    @staticmethod
    def _uuid_key(char_uuid: str) -> str:
        return char_uuid.lower()

    def __init__(
        self,
        address_or_device: str | BLEDevice,
        capture: CaptureLog | None = None,
    ) -> None:
        if isinstance(address_or_device, BLEDevice):
            self.address = address_or_device.address
            self._client = BleakClient(address_or_device)
        else:
            self.address = address_or_device
            self._client = BleakClient(address_or_device)
        self.capture = capture if capture is not None else NullCapture()
        self._write_lock = asyncio.Lock()
        self._notify_handlers: dict[str, list[Callable[[bytes], None]]] = {}
        self._notify_buffers: dict[str, list[bytes]] = {}
        self._subscribed: set[str] = set()
        self.gatt_timeout_s = DEFAULT_GATT_TIMEOUT_S

    async def _await_gatt(self, coro, *, op: str) -> object:
        try:
            return await asyncio.wait_for(coro, timeout=self.gatt_timeout_s)
        except asyncio.TimeoutError as exc:
            raise GattOperationTimeout(
                f"{op} timed out after {self.gatt_timeout_s:.0f}s — device may not support this command"
            ) from exc

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected

    @property
    def device_name(self) -> str | None:
        """Peripheral name after connect (plain str, safe for YAML)."""
        if not self._client.is_connected:
            return None
        try:
            from zephyr_re.settings import as_str

            return as_str(self._client.name)
        except Exception:
            return None

    async def connect(self, timeout: float = 25.0) -> None:
        await self._client.connect(timeout=timeout)
        self.capture.log("connect", message=f"Connected to {self.address}")

    async def disconnect(self) -> None:
        if self._client.is_connected:
            self.capture.log("disconnect", message=f"Disconnected from {self.address}")
            await self._client.disconnect()

    def enumerate_gatt(self) -> list[GattService]:
        services: list[GattService] = []
        for svc in self._client.services:
            chars = [
                GattCharacteristic.from_bleak(c, svc.uuid)
                for c in svc.characteristics
            ]
            services.append(GattService(uuid=svc.uuid, characteristics=chars))
        return services

    def find_characteristic(self, uuid: str) -> BleakGATTCharacteristic | None:
        target = uuid.lower()
        for svc in self._client.services:
            for char in svc.characteristics:
                if char.uuid.lower() == target:
                    return char
        return None

    def find_service(self, uuid: str) -> BleakGATTService | None:
        target = uuid.lower()
        for svc in self._client.services:
            if svc.uuid.lower() == target:
                return svc
        return None

    async def read(self, char_uuid: str, *, log: bool = True) -> bytes:
        char = self.find_characteristic(char_uuid)
        if char is None:
            raise ValueError(f"Characteristic not found: {char_uuid}")
        data = await self._await_gatt(
            self._client.read_gatt_char(char),
            op=f"read {char_uuid}",
        )
        assert isinstance(data, (bytes, bytearray))
        payload = bytes(data)
        if log:
            self.capture.log("read", characteristic=char_uuid, data=payload, message=None)
        return payload

    async def _write_gatt(
        self,
        char: BleakGATTCharacteristic,
        char_uuid: str,
        data: bytes,
        *,
        response: bool,
    ) -> None:
        await self._await_gatt(
            self._client.write_gatt_char(char, data, response=response),
            op=f"write {char_uuid}",
        )
        self.capture.log("write", characteristic=char_uuid, data=data, message=None)

    async def write(self, char_uuid: str, data: bytes, *, response: bool = True) -> None:
        char = self.find_characteristic(char_uuid)
        if char is None:
            raise ValueError(f"Characteristic not found: {char_uuid}")
        async with self._write_lock:
            await self._write_gatt(char, char_uuid, data, response=response)

    async def start_notify(self, char_uuid: str) -> None:
        key = self._uuid_key(char_uuid)
        if key in self._subscribed:
            return

        def _handler(_handle: int, data: bytearray) -> None:
            payload = bytes(data)
            self.capture.log("notify", characteristic=key, data=payload, message=None)
            self._notify_buffers.setdefault(key, []).append(payload)
            for cb in self._notify_handlers.get(key, []):
                cb(payload)

        char = self.find_characteristic(char_uuid)
        if char is None:
            raise ValueError(f"Characteristic not found: {char_uuid}")
        try:
            await self._client.start_notify(char, _handler)
        except ValueError as exc:
            if "already started" in str(exc).lower():
                self.capture.log("info", characteristic=key, message="Notify already active")
            else:
                raise
        self._subscribed.add(key)

    async def stop_notify(self, char_uuid: str) -> None:
        key = self._uuid_key(char_uuid)
        if key not in self._subscribed:
            return
        char = self.find_characteristic(char_uuid)
        if char is not None:
            await self._client.stop_notify(char)
        self._subscribed.discard(key)

    def add_notify_handler(self, char_uuid: str, callback: Callable[[bytes], None]) -> None:
        self._notify_handlers.setdefault(self._uuid_key(char_uuid), []).append(callback)

    def drain_notifications(self, char_uuid: str) -> list[bytes]:
        return self._notify_buffers.pop(self._uuid_key(char_uuid), [])

    def clear_notifications(self, char_uuid: str | None = None) -> None:
        if char_uuid is None:
            self._notify_buffers.clear()
        else:
            self._notify_buffers.pop(self._uuid_key(char_uuid), None)

    async def subscribe_uuids(self, uuids: list[str | None]) -> list[str]:
        """Subscribe to a list of notify characteristics (skips missing/null)."""
        subscribed: list[str] = []
        for uuid in uuids:
            if not uuid:
                continue
            if self.find_characteristic(uuid) is None:
                self.capture.log("info", characteristic=uuid, message="Notify char not on device")
                continue
            try:
                await self.start_notify(uuid)
                subscribed.append(uuid)
            except Exception as exc:
                self.capture.log(
                    "info",
                    characteristic=uuid,
                    message=f"Failed to subscribe: {exc}",
                )
        return subscribed

    async def subscribe_all_notifications(self) -> list[str]:
        """Subscribe to every notify/indicate characteristic. Returns UUIDs subscribed."""
        subscribed: list[str] = []
        for svc in self.enumerate_gatt():
            for char in svc.characteristics:
                if "notify" in char.properties or "indicate" in char.properties:
                    try:
                        await self.start_notify(char.uuid)
                        subscribed.append(char.uuid)
                    except Exception as exc:
                        self.capture.log(
                            "info",
                            characteristic=char.uuid,
                            message=f"Failed to subscribe: {exc}",
                        )
        return subscribed

    async def wait_for_notifications(
        self,
        char_uuid: str,
        timeout_ms: int = 500,
        *,
        clear_first: bool = True,
    ) -> list[bytes]:
        if clear_first:
            self.clear_notifications(char_uuid)
        await asyncio.sleep(timeout_ms / 1000.0)
        return self.drain_notifications(char_uuid)

    async def exchange(
        self,
        write_char_uuid: str,
        data: bytes,
        notify_char_uuid: str | None = None,
        timeout_ms: int = 500,
        *,
        response: bool = True,
    ) -> list[bytes]:
        """Write and collect notifications (serialized)."""
        if notify_char_uuid:
            await self.start_notify(notify_char_uuid)
            self.clear_notifications(notify_char_uuid)
        char = self.find_characteristic(write_char_uuid)
        if char is None:
            raise ValueError(f"Characteristic not found: {write_char_uuid}")
        async with self._write_lock:
            await self._write_gatt(char, write_char_uuid, data, response=response)
            if notify_char_uuid:
                return await self.wait_for_notifications(
                    notify_char_uuid, timeout_ms, clear_first=False
                )
        return []
