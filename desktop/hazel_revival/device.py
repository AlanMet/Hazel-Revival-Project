"""Device layer — wraps zephyr_re.Zephyr with web-app-shaped results."""

from __future__ import annotations

from zephyr_re.protocol.base import CommandStatus
from zephyr_re.protocol.packets import WAVE_RATE_FAST, WAVE_RATE_MEDIUM, WAVE_RATE_SLOW
from zephyr_re.zephyr import Zephyr


def _display_name(zephyr: Zephyr) -> str:
    selected = getattr(zephyr.connector, "_selected", None)
    name = getattr(selected, "name", None) if selected else None
    if isinstance(name, str) and "zephyr" in name.lower():
        return name
    client = zephyr.connector.client
    if client and getattr(client, "device_name", None):
        dn = client.device_name
        if isinstance(dn, str) and "zephyr" in dn.lower():
            return dn
    return "Razer Zephyr"


def _result(label: str, cmd) -> dict:
    ok = cmd.status == CommandStatus.OK
    return {"ok": ok, "message": cmd.message if ok else f"{label} — no device ack"}


class DeviceController:
    def __init__(self) -> None:
        self.zephyr = Zephyr()

    @property
    def is_connected(self) -> bool:
        return self.zephyr.is_connected

    @property
    def device_name(self) -> str:
        return _display_name(self.zephyr)

    async def connect(self) -> dict:
        try:
            await self.zephyr.connect()
            name = self.device_name
            return {"ok": True, "message": f"Connected to {name}", "name": name}
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    async def disconnect(self) -> dict:
        await self.zephyr.disconnect()
        return {"ok": True, "message": "Disconnected"}

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

    async def external_wave(self, rate: int = WAVE_RATE_MEDIUM) -> dict:
        return _result("External wave", await self.zephyr.external_wave(rate=rate))

    async def external_off(self) -> dict:
        return _result("External off", await self.zephyr.external_off())
