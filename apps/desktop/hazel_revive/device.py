"""App-facing device facade over zephyr_re."""

from __future__ import annotations

from zephyr_re.ble.scanner import BleDevice
from zephyr_re.device.state import DeviceState
from zephyr_re.protocol.base import CommandStatus, FanSpeed
from zephyr_re.protocol.packets import WAVE_RATE_FAST, WAVE_RATE_MEDIUM, WAVE_RATE_SLOW
from zephyr_re.zephyr import Zephyr


def _display_name(zephyr: Zephyr) -> str:
    selected = getattr(zephyr.connector, "_selected", None)
    name = getattr(selected, "name", None) if selected else None
    if isinstance(name, str) and name.strip():
        return name
    client = zephyr.connector.client
    if client and getattr(client, "device_name", None):
        return str(client.device_name)
    return "Razer Zephyr"


def _result(label: str, cmd) -> dict:
    ok = cmd.status == CommandStatus.OK
    return {"ok": ok, "message": cmd.message if ok else f"{label} — {cmd.message}"}


class DeviceController:
    def __init__(self) -> None:
        self.zephyr = Zephyr()
        self.state: DeviceState | None = None

    @property
    def is_connected(self) -> bool:
        return self.zephyr.is_connected

    @property
    def device_name(self) -> str:
        return _display_name(self.zephyr)

    async def scan(self, *, timeout: float = 8.0) -> list[BleDevice]:
        return await self.zephyr.scan(timeout=timeout)

    async def connect(self, device: BleDevice | None = None) -> dict:
        try:
            if device is not None:
                await self.zephyr.connect_to(device)
            else:
                await self.zephyr.connect()
            self.state = await self.zephyr.sync_state()
            return {
                "ok": True,
                "message": f"Connected to {self.device_name}",
                "name": self.device_name,
                "state": self.state,
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    async def disconnect(self) -> dict:
        await self.zephyr.disconnect()
        self.state = None
        return {"ok": True, "message": "Disconnected"}

    async def sync(self) -> dict:
        try:
            self.state = await self.zephyr.sync_state()
            return {"ok": True, "state": self.state}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def on_fan_changed(self, callback) -> None:
        def _wrap(speed: FanSpeed) -> None:
            if self.state is not None:
                self.state.fan_speed = speed
                self.state.fan_speed_source = "notify"
            callback(speed)

        self.zephyr.on_fan_notify(_wrap)

    async def fan_low(self) -> dict:
        return _result("Fan low", await self.zephyr.fan_low())

    async def fan_high(self) -> dict:
        return _result("Fan high", await self.zephyr.fan_high())

    async def fan_off(self) -> dict:
        return _result("Fan off", await self.zephyr.fan_off())

    async def internal_static(self, r: int, g: int, b: int) -> dict:
        return _result("Internal static", await self.zephyr.internal_static(r, g, b))

    async def internal_spectrum(self) -> dict:
        return _result("Internal spectrum", await self.zephyr.internal_spectrum())

    async def internal_breathing(self) -> dict:
        return _result("Internal breathing", await self.zephyr.internal_breathing())

    async def internal_off(self) -> dict:
        return _result("Internal off", await self.zephyr.internal_off())

    async def external_static(self, r: int, g: int, b: int) -> dict:
        return _result("External static", await self.zephyr.external_static(r, g, b))

    async def external_spectrum(self) -> dict:
        return _result("External spectrum", await self.zephyr.external_spectrum())

    async def external_breathing(self) -> dict:
        return _result("External breathing", await self.zephyr.external_breathing())

    async def external_wave(self, *, left_to_right: bool = True, rate: int = WAVE_RATE_MEDIUM) -> dict:
        return _result(
            "External wave",
            await self.zephyr.external_wave(left_to_right=left_to_right, rate=rate),
        )

    async def external_off(self) -> dict:
        return _result("External off", await self.zephyr.external_off())

    @staticmethod
    def wave_presets() -> dict[str, int]:
        return {
            "slow": WAVE_RATE_SLOW,
            "medium": WAVE_RATE_MEDIUM,
            "fast": WAVE_RATE_FAST,
        }
