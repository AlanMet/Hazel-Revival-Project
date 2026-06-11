"""YAML-driven protocol backend — send commands from reverse-engineering/tools/config/gatt_map.yaml."""

from __future__ import annotations

from typing import Any

from zephyr_re.ble.client import BleClient
from zephyr_re_dev.config import CommandSpec, GattMapConfig
from zephyr_re.protocol.base import (
    BatteryInfo,
    ColorInfo,
    CommandResult,
    CommandStatus,
    FanSpeed,
    ProtocolBackend,
)
from zephyr_re.util.hexio import format_hex, parse_hex


class YamlBackend(ProtocolBackend):
    name = "yaml"

    def __init__(self, config: GattMapConfig | None = None) -> None:
        self.config = config or GattMapConfig.load()
        self._client: BleClient | None = None
        self._req_id = self.config.request_id_start

    @property
    def configured(self) -> bool:
        return self.config.is_configured()

    async def on_connect(self, client: BleClient) -> None:
        self._client = client
        for notify_uuid in (
            self.config.notify_char_uuid,
            self.config.extra_notify_char_uuid,
        ):
            if not notify_uuid:
                continue
            try:
                await client.start_notify(notify_uuid)
            except Exception as exc:
                client.capture.log("info", message=f"[yaml] notify subscribe {notify_uuid}: {exc}")
        if self.configured:
            client.capture.log("info", message="[yaml] Backend ready with configured UUIDs")
        else:
            client.capture.log(
                "info",
                message="[yaml] write_char_uuid / notify_char_uuid not set — edit reverse-engineering/tools/config/gatt_map.yaml",
            )

    def _next_req_id(self) -> int:
        rid = self._req_id
        self._req_id = (self._req_id + 1) & 0xFF
        return rid

    def _format_command(self, template: str, **kwargs: Any) -> bytes:
        # Replace {req} with next request id if present
        if "{req" in template:
            kwargs.setdefault("req", self._next_req_id())
        formatted = template.format(**kwargs)
        return parse_hex(formatted)

    async def _run_command(self, spec: CommandSpec | None, **fmt: Any) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        if spec is None or not spec.write_templates():
            return CommandResult(CommandStatus.NOT_CONFIGURED, "Command not defined in gatt_map.yaml")
        if not self.configured:
            return CommandResult(
                CommandStatus.NOT_CONFIGURED,
                "Set write_char_uuid and notify_char_uuid in reverse-engineering/tools/config/gatt_map.yaml",
            )
        write_uuid = self.config.write_char_uuid
        notify_uuid = self.config.notify_char_uuid if spec.expect_notify else None
        assert write_uuid is not None
        try:
            templates = spec.write_templates()
            sent: list[bytes] = []
            frames: list[bytes] = []
            for idx, template in enumerate(templates):
                data = self._format_command(template, **fmt)
                sent.append(data)
                if idx == len(templates) - 1 and spec.expect_notify:
                    frames = await self._client.exchange(
                        write_uuid,
                        data,
                        notify_uuid,
                        timeout_ms=spec.response_timeout_ms,
                    )
                else:
                    await self._client.write(write_uuid, data, response=True)
            hex_sent = " | ".join(format_hex(chunk) for chunk in sent)
            return CommandResult(CommandStatus.OK, f"Sent {spec.name}: {hex_sent}", frames)
        except Exception as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))

    async def read_battery(self) -> BatteryInfo | None:
        result = await self._run_command(self.config.commands.get("read_battery"))
        if not result.ok:
            return BatteryInfo(percent=None, message=result.message)
        pct = None
        for frame in result.responses or []:
            if len(frame) >= 9:
                val = frame[8]
                if val <= 100:
                    pct = val
                    break
            if len(frame) >= 1 and frame[0] <= 100:
                pct = frame[0]
        return BatteryInfo(percent=pct, message=result.message if pct is None else None)

    async def read_external_color(self) -> ColorInfo | None:
        result = await self._run_command(self.config.commands.get("read_external_color"))
        if not result.ok or not result.responses:
            return None
        for frame in result.responses:
            if len(frame) >= 12:
                data = frame[8:]
                if len(data) >= 8 and data[0] == 0x04:
                    return ColorInfo(r=data[5], g=data[6], b=data[7])
        return None

    async def read_external_brightness(self) -> int | None:
        return None

    async def read_external_effect(self) -> str | None:
        return None

    async def set_external_color(self, r: int, g: int, b: int) -> CommandResult:
        return await self._run_command(
            self.config.commands.get("set_external_color"),
            r=r,
            g=g,
            b=b,
        )

    async def set_external_brightness(self, brightness: int) -> CommandResult:
        return await self._run_command(
            self.config.commands.get("set_external_brightness"),
            brightness=max(0, min(255, brightness)),
        )

    async def set_external_effect(self, effect: str, **opts: Any) -> CommandResult:
        key = {
            "static": "set_external_effect_static",
            "breathing": "set_external_effect_breathing",
            "spectrum": "set_external_effect_spectrum",
            "wave": "set_external_effect_wave",
            "off": "set_external_effect_off",
        }.get(effect.lower())
        if key:
            spec = self.config.commands.get(key)
            if spec and spec.write_templates():
                return await self._run_command(spec, **opts)
        return CommandResult(
            CommandStatus.NOT_CONFIGURED,
            f"No Hazel effect command for {effect!r} in gatt_map.yaml",
        )

    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0) -> CommandResult:
        key = "set_internal_light_on" if on else "set_internal_light_off"
        spec = self.config.commands.get(key)
        if on and r == 0 and g == 0 and b == 0:
            r, g, b = 0, 255, 0
        if spec and spec.write_templates():
            return await self._run_command(spec, r=r, g=g, b=b)
        return CommandResult(CommandStatus.NOT_CONFIGURED, f"{key} not defined in gatt_map.yaml")

    async def set_internal_brightness(self, brightness: int) -> CommandResult:
        return await self._run_command(
            self.config.commands.get("set_internal_brightness"),
            brightness=max(0, min(255, brightness)),
        )

    async def set_internal_effect(self, effect: str, **opts: Any) -> CommandResult:
        key = {
            "static": "set_internal_effect_static",
            "breathing": "set_internal_effect_breathing",
            "spectrum": "set_internal_effect_spectrum",
            "off": "set_internal_effect_off",
        }.get(effect.lower())
        if key:
            spec = self.config.commands.get(key)
            if spec and spec.write_templates():
                return await self._run_command(spec, **opts)
        return CommandResult(
            CommandStatus.NOT_CONFIGURED,
            f"No Hazel internal effect command for {effect!r} in gatt_map.yaml",
        )

    async def set_fan_speed(self, speed: FanSpeed) -> CommandResult:
        key = {
            FanSpeed.OFF: "set_fan_off",
            FanSpeed.LOW: "set_fan_low",
            FanSpeed.HIGH: "set_fan_high",
        }[speed]
        return await self._run_command(self.config.commands.get(key))

    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        target = char_uuid or self.config.write_char_uuid
        if not target:
            return CommandResult(CommandStatus.NOT_CONFIGURED, "No write characteristic configured")
        try:
            data = parse_hex(write_hex)
            notify = self.config.notify_char_uuid
            frames = await self._client.exchange(target, data, notify, timeout_ms=500)
            return CommandResult(CommandStatus.OK, "Raw exchange complete", frames)
        except Exception as exc:
            return CommandResult(CommandStatus.ERROR, str(exc))
