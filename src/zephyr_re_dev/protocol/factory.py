"""Protocol backend factory."""

from __future__ import annotations

from zephyr_re.ble.client import BleClient
from zephyr_re_dev.config import GattMapConfig
from zephyr_re.protocol.base import ProtocolBackend
from zephyr_re_dev.protocol.razer_vendor import RazerVendorProbe
from zephyr_re_dev.protocol.stub import StubBackend
from zephyr_re_dev.protocol.yaml_backend import YamlBackend

BACKEND_NAMES = ("stub", "razer_probe", "yaml", "auto")


def create_backend(name: str, config: GattMapConfig | None = None) -> ProtocolBackend:
    if name == "stub":
        return StubBackend()
    if name == "razer_probe":
        return RazerVendorProbe()
    if name == "yaml":
        return YamlBackend(config)
    if name == "auto":
        return AutoBackend(config)
    raise ValueError(f"Unknown backend: {name}. Choose from {BACKEND_NAMES}")


class AutoBackend(ProtocolBackend):
    """Try razer_probe, then yaml if configured, else stub."""

    name = "auto"

    def __init__(self, config: GattMapConfig | None = None) -> None:
        self._config = config or GattMapConfig.load()
        self._active: ProtocolBackend = StubBackend()

    @property
    def active_backend(self) -> ProtocolBackend:
        return self._active

    async def on_connect(self, client: BleClient) -> None:
        razer = RazerVendorProbe()
        await razer.on_connect(client)
        if razer.available:
            self._active = razer
            client.capture.log("info", message="[auto] Selected razer_probe backend")
            return

        yaml_backend = YamlBackend(self._config)
        await yaml_backend.on_connect(client)
        if yaml_backend.configured:
            self._active = yaml_backend
            client.capture.log("info", message="[auto] Selected yaml backend")
            return

        stub = StubBackend()
        await stub.on_connect(client)
        self._active = stub
        client.capture.log("info", message="[auto] Falling back to stub backend")

    async def read_battery(self):
        return await self._active.read_battery()

    async def read_external_color(self):
        return await self._active.read_external_color()

    async def read_external_brightness(self):
        return await self._active.read_external_brightness()

    async def read_external_effect(self):
        return await self._active.read_external_effect()

    async def set_external_color(self, r: int, g: int, b: int):
        return await self._active.set_external_color(r, g, b)

    async def set_external_brightness(self, brightness: int):
        return await self._active.set_external_brightness(brightness)

    async def set_external_effect(self, effect: str, **opts):
        return await self._active.set_external_effect(effect, **opts)

    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0):
        return await self._active.set_internal_light(on, r, g, b)

    async def set_internal_brightness(self, brightness: int):
        return await self._active.set_internal_brightness(brightness)

    async def set_internal_effect(self, effect: str, **opts):
        return await self._active.set_internal_effect(effect, **opts)

    async def set_fan_speed(self, speed):
        return await self._active.set_fan_speed(speed)

    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None):
        return await self._active.raw_exchange(write_hex, char_uuid)
