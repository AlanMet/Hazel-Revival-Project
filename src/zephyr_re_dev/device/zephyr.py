"""High-level Zephyr device API — used by CLI and future GUI."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from zephyr_re_dev.ble.capture import GattCaptureLog
from zephyr_re.ble.client import BleClient, GattService
from zephyr_re_dev.ble.gatt_read import (
    GattReadResult,
    NotifyCapture,
    format_read_results,
    listen_notifications as capture_notifications,
    read_all_readable,
)
from zephyr_re.ble.macos_retrieve import resolve_macos_peripheral
from zephyr_re.ble.scanner import BleDevice, find_zephyr_target, refresh_live_target
from zephyr_re_dev.config import GattMapConfig, as_str, project_root, save_known_device
from zephyr_re_dev.protocol.razer_vendor import (
    RAZER_VENDOR_SERVICE,
    RAZER_VENDOR_WRITE,
    RazerVendorProbe,
)
from zephyr_re.protocol.base import (
    BatteryInfo,
    ColorInfo,
    CommandResult,
    CommandStatus,
    FanSpeed,
    ProtocolBackend,
)
from zephyr_re_dev.protocol.probe_runner import (
    ProbeAttempt,
    probe_external_color as run_color_probe,
    probe_external_effect_static,
    probe_external_static_then_color,
    probe_fan_speed,
    probe_firmware_effect_id_sweep_result,
    probe_hazel_extras_result,
    restore_hazel_led_timeout_result,
    probe_internal_light,
    probe_vendor_reads,
)
from zephyr_re_dev.device.state import DeviceState
from zephyr_re_dev.protocol.factory import create_backend
from zephyr_re_dev.protocol.zephyr_parse import (
    INTERNAL_LIGHT_ZONE,
    brightness_to_percent,
    format_internal_light,
    latest_fan_from_frames,
    parse_brightness,
    parse_charging_state,
    parse_firmware_version,
    resolve_brightness,
    resolve_fan_speed,
    resolve_internal_light,
    resolve_zone_chroma,
)

TRACE_POLL_INTERVAL_S = 20.0


def _battery_percent_from_gatt(reads: list[GattReadResult]) -> int | None:
    for result in reads:
        if not result.ok or not result.data:
            continue
        if "2a19" not in result.char_uuid.lower():
            continue
        val = result.data[0]
        return val if val <= 100 else round(val * 100 / 255)
    return None


def _extra_notify_gatt_data(reads: list[GattReadResult]) -> bytes | None:
    for result in reads:
        if not result.ok or not result.data:
            continue
        if "52401526" in result.char_uuid.lower():
            return result.data
    return None


@dataclass
class ConnectionInfo:
    address: str
    name: str | None
    backend: str
    connected_at: str


@dataclass
class ConnectSummary:
    name: str | None
    address: str
    backend: str
    service_count: int
    characteristic_count: int
    vendor_gatt: bool
    battery_gatt: bool
    notify_subscriptions: int


class ZephyrDevice:
    """Facade over BLE client and protocol backend."""

    def __init__(
        self,
        backend_name: str = "auto",
        config: GattMapConfig | None = None,
    ) -> None:
        self.config = config or GattMapConfig.load()
        self._backend_name = backend_name
        self._backend: ProtocolBackend = create_backend(backend_name, self.config)
        self._session_capture = GattCaptureLog()
        self._client: BleClient | None = None
        self._selected: BleDevice | None = None
        self._connection_info: ConnectionInfo | None = None
        self._notify_subscription_count: int = 0
        self._trace_task: asyncio.Task[None] | None = None
        self._last_poll: dict[str, bytes] = {}
        self._last_state: DeviceState | None = None

    @property
    def is_connected(self) -> bool:
        return self._client is not None and self._client.is_connected

    @property
    def capture(self) -> GattCaptureLog:
        return self._session_capture

    @property
    def live_log_path(self) -> Path | None:
        return self._session_capture.live_path

    @property
    def backend_name(self) -> str:
        return self._backend_name

    @property
    def active_protocol_name(self) -> str:
        return self._backend.name

    @property
    def vendor_available(self) -> bool:
        if not self._client:
            return False
        return self._client.find_characteristic(RAZER_VENDOR_WRITE) is not None

    @property
    def last_state(self) -> DeviceState | None:
        return self._last_state

    def _active_backend(self) -> ProtocolBackend:
        active = self._backend
        if hasattr(active, "active_backend"):
            return active.active_backend  # type: ignore[attr-defined]
        return active

    @property
    def selected_device(self) -> BleDevice | None:
        return self._selected

    @property
    def connection_info(self) -> ConnectionInfo | None:
        return self._connection_info

    def set_backend(self, name: str) -> None:
        self._backend_name = name
        self._backend = create_backend(name, self.config)
        if self._client and self.is_connected:
            # Re-run on_connect for new backend (sync wrapper in CLI via asyncio)
            pass

    def select_device(self, device: BleDevice) -> None:
        self._selected = device

    def build_connect_summary(self) -> ConnectSummary | None:
        if not self.is_connected or self._connection_info is None:
            return None
        services = self.enumerate_gatt()
        char_count = sum(len(s.characteristics) for s in services)
        vendor = any(s.uuid.lower() == RAZER_VENDOR_SERVICE.lower() for s in services)
        battery = any(s.uuid.lower() == "0000180f-0000-1000-8000-00805f9b34fb" for s in services)
        return ConnectSummary(
            name=self._connection_info.name,
            address=self._connection_info.address,
            backend=self._connection_info.backend,
            service_count=len(services),
            characteristic_count=char_count,
            vendor_gatt=vendor,
            battery_gatt=battery,
            notify_subscriptions=self._notify_subscription_count,
        )

    async def connect_foolproof(self, *, retries: int = 3) -> ConnectSummary:
        """Find Zephyr (advertising or system-connected), then open GATT."""
        target = await find_zephyr_target(self.config.device_name_patterns)
        self.select_device(target)
        return await self.connect(retries=retries)

    async def connect(
        self,
        address: str | None = None,
        *,
        force: bool = False,
        retries: int = 3,
    ) -> ConnectSummary:
        selected = self._selected
        addr = address or (selected.address if selected else None)
        if not addr:
            raise ValueError("No device selected")
        device_name = as_str(selected.name) if selected else None

        if (
            not force
            and self._client
            and self._client.is_connected
            and self._client.address == addr
        ):
            summary = self.build_connect_summary()
            assert summary is not None
            return summary

        if self._client and self._client.is_connected:
            await self.disconnect()

        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                return await self._connect_once(
                    addr,
                    device_name=device_name,
                    attempt=attempt,
                )
            except Exception as exc:
                last_error = exc
                if self._client and self._client.is_connected:
                    await self.disconnect()
                if attempt < retries:
                    import asyncio

                    await asyncio.sleep(1.5)
                    target = await refresh_live_target(
                        addr,
                        self.config.device_name_patterns,
                    )
                    self.select_device(target)
                    addr = target.address
                    device_name = as_str(target.name) or device_name

        assert last_error is not None
        raise last_error

    async def _connect_once(
        self,
        addr: str,
        *,
        device_name: str | None,
        attempt: int,
    ) -> ConnectSummary:
        bleak_device = None
        if self._selected and self._selected.bleak_device is not None:
            bleak_device = self._selected.bleak_device
        if bleak_device is None:
            bleak_device = await resolve_macos_peripheral(
                addr,
                name_patterns=self.config.device_name_patterns,
            )
        if bleak_device is not None:
            self._client = BleClient(bleak_device, capture=self._session_capture)
        else:
            # Fall back: Bleak scans briefly for the UUID (device may be advertising).
            self._client = BleClient(addr, capture=self._session_capture)
        self._session_capture.log("info", message=f"Connect attempt {attempt} → {addr}")
        await self._client.connect()
        self._backend = create_backend(self._backend_name, self.config)
        await self._backend.on_connect(self._client)
        notify_subs = await self._client.subscribe_uuids(
            [
                self.config.notify_char_uuid,
                self.config.extra_notify_char_uuid,
                self.config.battery_service_char_uuid,
            ]
        )
        extra_notify = await self._client.subscribe_all_notifications()
        for uuid in extra_notify:
            if uuid not in notify_subs:
                notify_subs.append(uuid)
        self._notify_subscription_count = len(notify_subs)
        self._start_background_trace()
        connected_name = device_name or self._client.device_name
        self._connection_info = ConnectionInfo(
            address=addr,
            name=connected_name,
            backend=self._backend.name,
            connected_at=datetime.now(timezone.utc).isoformat(),
        )
        save_known_device(addr, self._connection_info.name)
        self._append_gatt_snapshot()
        summary = self.build_connect_summary()
        assert summary is not None
        return summary

    async def disconnect(self) -> None:
        self._stop_background_trace()
        if self._client:
            await self._client.disconnect()
        self._connection_info = None

    def _start_background_trace(self) -> None:
        self._stop_background_trace()
        self._trace_task = asyncio.create_task(self._background_trace_loop())

    def _stop_background_trace(self) -> None:
        if self._trace_task is not None:
            self._trace_task.cancel()
            self._trace_task = None

    async def _background_trace_loop(self) -> None:
        """Periodically read all GATT characteristics and log spontaneous notifies."""
        try:
            while self.is_connected and self._client is not None:
                await asyncio.sleep(TRACE_POLL_INTERVAL_S)
                if not self.is_connected or self._client is None:
                    break
                try:
                    results = await read_all_readable(self._client, log_reads=False)
                    changed = 0
                    for r in results:
                        if not r.ok or r.data is None:
                            continue
                        key = r.char_uuid.lower()
                        if self._last_poll.get(key) == r.data:
                            continue
                        self._last_poll[key] = r.data
                        changed += 1
                        from zephyr_re_dev.util.frame_decode import decode_gatt_payload

                        hint = r.hint or decode_gatt_payload(r.char_uuid, r.data)
                        self._session_capture.log(
                            "poll",
                            characteristic=r.char_uuid,
                            data=r.data,
                            message=hint,
                        )
                    if changed:
                        self._session_capture.log(
                            "info",
                            message=f"background poll: {changed} characteristic(s) changed",
                        )
                except Exception as exc:
                    self._session_capture.log("info", message=f"background poll failed: {exc}")
        except asyncio.CancelledError:
            pass

    def enumerate_gatt(self) -> list[GattService]:
        if not self._client:
            return []
        return self._client.enumerate_gatt()

    def _append_gatt_snapshot(self) -> None:
        services = self.enumerate_gatt()
        if not services:
            return
        path = project_root() / "research" / "gatt-map.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"\n## Snapshot {datetime.now(timezone.utc).isoformat()}",
            f"Address: `{self._client.address if self._client else '?'}`",
            "",
        ]
        for svc in services:
            lines.append(f"### Service `{svc.uuid}`")
            for char in svc.characteristics:
                props = ", ".join(char.properties) or "none"
                lines.append(f"- `{char.uuid}` handle={char.handle} [{props}]")
            lines.append("")
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))

    async def read_all_gatt(self) -> list[GattReadResult]:
        if not self._client:
            return []
        return await read_all_readable(self._client)

    async def read_external_brightness(self) -> int | None:
        return await self._backend.read_external_brightness()

    async def read_external_effect(self) -> str | None:
        return await self._backend.read_external_effect()

    async def fetch_device_state(self) -> DeviceState:
        """Read GATT baseline + vendor lighting state for sync / settings UI."""
        gatt_reads = await self.read_all_gatt()
        battery = _battery_percent_from_gatt(gatt_reads)
        if battery is None:
            info = await self.read_battery()
            if info and info.percent is not None:
                battery = info.percent

        vendor_raw: dict[str, list[bytes]] = {}
        extra_raw: list[bytes] = []
        extra_gatt = _extra_notify_gatt_data(gatt_reads)
        brightness: int | None = None
        internal_brightness: int | None = None
        color: ColorInfo | None = None
        color_note: str | None = None
        effect: str | None = None
        internal_effect: str | None = None
        fan_speed = FanSpeed.OFF
        fan_source = "assumed"
        internal_on: bool | None = None
        internal_color: ColorInfo | None = None
        internal_zone: int | None = INTERNAL_LIGHT_ZONE
        internal_light = "unknown"
        firmware_version: str | None = None
        is_charging: bool | None = None

        active = self._active_backend()
        if isinstance(active, RazerVendorProbe) and active.available:
            sync = await active.read_vendor_sync_raw()
            if sync is not None:
                vendor_raw = {
                    "brightness_external": sync.brightness_external,
                    "brightness_internal": sync.brightness_internal,
                    "effect_external": sync.effect_external,
                    "effect_internal": sync.effect_internal,
                    "fan": sync.fan,
                    "firmware": sync.firmware,
                    "charging": sync.charging,
                }
                extra_raw = list(sync.extra)
                brightness = resolve_brightness(
                    sync.brightness_external,
                    sync.extra,
                    header_req=sync.brightness_external_req,
                )
                internal_brightness = parse_brightness(
                    sync.brightness_internal,
                    header_req=sync.brightness_internal_req,
                )
                external_zone = resolve_zone_chroma(sync.effect_external)
                effect = external_zone.effect if external_zone.effect != "unknown" else None
                color = external_zone.color
                color_note = external_zone.color_note
                internal_zone_state = resolve_zone_chroma(sync.effect_internal)
                internal_effect = (
                    internal_zone_state.effect
                    if internal_zone_state.effect != "unknown"
                    else None
                )
                internal_on, internal_color = resolve_internal_light(sync.effect_internal)
                internal_light = format_internal_light(
                    internal_on,
                    internal_color,
                    zone=internal_zone,
                )
                fan_speed, fan_source = resolve_fan_speed(
                    sync.fan,
                    sync.extra,
                    extra_gatt=extra_gatt,
                )
                firmware_version = parse_firmware_version(sync.firmware)
                is_charging = parse_charging_state(sync.charging)
        else:
            brightness = await self.read_external_brightness()
            color = await self.read_external_color()
            effect = await self.read_external_effect()

        brightness_pct = brightness_to_percent(brightness) if brightness is not None else None
        internal_brightness_pct = (
            brightness_to_percent(internal_brightness) if internal_brightness is not None else None
        )

        state = DeviceState(
            battery_percent=battery,
            external_brightness=brightness,
            external_brightness_percent=brightness_pct,
            internal_brightness=internal_brightness,
            internal_brightness_percent=internal_brightness_pct,
            external_color=color,
            external_effect=effect,
            external_color_note=color_note,
            internal_effect=internal_effect,
            fan_speed=fan_speed,
            fan_speed_source=fan_source,
            internal_light=internal_light,
            internal_light_on=internal_on,
            internal_light_color=internal_color,
            internal_light_zone=internal_zone,
            firmware_version=firmware_version,
            is_charging=is_charging,
            gatt_reads=gatt_reads,
            vendor_raw=vendor_raw,
            extra_raw=extra_raw,
            synced_at=datetime.now(timezone.utc).isoformat(),
        )
        self._last_state = state
        return state

    def apply_listen_to_state(self, captures: list[NotifyCapture]) -> None:
        """Update fan speed (and extra frames) from passive 52401526 listen traffic."""
        if self._last_state is None:
            return
        extra_frames: list[bytes] = []
        for cap in captures:
            if "52401526" not in cap.char_uuid.lower():
                continue
            extra_frames.extend(cap.frames)
        if not extra_frames:
            return
        self._last_state.extra_raw.extend(extra_frames)
        fan = latest_fan_from_frames(extra_frames)
        if fan is not None:
            self._last_state.fan_speed = fan
            self._last_state.fan_speed_source = "listen"

    async def listen_notifications(self, duration_s: float = 30.0) -> list[NotifyCapture]:
        if not self._client:
            return []
        return await capture_notifications(self._client, duration_s=duration_s)

    async def probe_vendor_reads(self, *, on_attempt=None) -> list[ProbeAttempt]:
        if not self._client:
            return []
        return await probe_vendor_reads(self._client, on_attempt=on_attempt)

    def append_read_snapshot(self, results: list[GattReadResult]) -> Path:
        path = project_root() / "research" / "gatt-reads.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(
                "# GATT Read Snapshots\n\nDirect reads of every readable characteristic.\n\n",
                encoding="utf-8",
            )
        lines = [
            f"\n## Snapshot {datetime.now(timezone.utc).isoformat()}",
            f"Address: `{self._client.address if self._client else '?'}`",
            "",
            *format_read_results(results),
            "",
        ]
        with path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return path

    async def read_battery(self) -> BatteryInfo | None:
        return await self._backend.read_battery()

    async def read_external_color(self) -> ColorInfo | None:
        return await self._backend.read_external_color()

    async def set_external_color(self, r: int, g: int, b: int) -> CommandResult:
        return await self._backend.set_external_color(r, g, b)

    async def probe_external_color(
        self,
        r: int,
        g: int,
        b: int,
        *,
        on_attempt=None,
    ) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await run_color_probe(self._client, r, g, b, on_attempt=on_attempt)

    async def probe_static_effect(self, *, on_attempt=None) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_external_effect_static(self._client, on_attempt=on_attempt)

    async def probe_static_then_color(
        self,
        r: int,
        g: int,
        b: int,
        *,
        on_attempt=None,
    ) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_external_static_then_color(
            self._client, r, g, b, on_attempt=on_attempt
        )

    async def probe_internal_light_writes(
        self,
        r: int,
        g: int,
        b: int,
        *,
        on_attempt=None,
    ) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_internal_light(self._client, r, g, b, on_attempt=on_attempt)

    async def probe_fan_writes(self, fan: int, *, on_attempt=None) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_fan_speed(self._client, fan, on_attempt=on_attempt)

    async def probe_hazel_extras(self, *, on_attempt=None) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_hazel_extras_result(self._client, on_attempt=on_attempt)

    async def restore_hazel_led_timeout(self) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await restore_hazel_led_timeout_result(self._client)

    async def probe_firmware_effect_ids(
        self,
        zone: int,
        *,
        id_start: int = 0,
        id_end: int = 15,
        on_attempt=None,
    ) -> CommandResult:
        if not self._client:
            return CommandResult(CommandStatus.ERROR, "Not connected")
        return await probe_firmware_effect_id_sweep_result(
            self._client,
            zone,
            id_start=id_start,
            id_end=id_end,
            on_attempt=on_attempt,
        )

    async def set_external_brightness(self, brightness: int) -> CommandResult:
        return await self._backend.set_external_brightness(brightness)

    async def set_external_effect(self, effect: str, **opts: Any) -> CommandResult:
        return await self._backend.set_external_effect(effect, **opts)

    async def set_internal_light(self, on: bool, r: int = 0, g: int = 0, b: int = 0) -> CommandResult:
        return await self._backend.set_internal_light(on, r, g, b)

    async def set_internal_brightness(self, brightness: int) -> CommandResult:
        return await self._backend.set_internal_brightness(brightness)

    async def set_internal_effect(self, effect: str, **opts: Any) -> CommandResult:
        return await self._backend.set_internal_effect(effect, **opts)

    async def set_fan_speed(self, speed: FanSpeed) -> CommandResult:
        return await self._backend.set_fan_speed(speed)

    async def raw_exchange(self, write_hex: str, char_uuid: str | None = None) -> CommandResult:
        return await self._backend.raw_exchange(write_hex, char_uuid)

    async def send_vendor_writes(
        self,
        label: str,
        writes: list[bytes],
        *,
        timeout_ms: int = 1500,
    ) -> tuple[list[bytes], bool]:
        """Hazel two-packet write(s) to 52401524; returns (notify frames, ack)."""
        if not self._client:
            raise RuntimeError("Not connected")
        from zephyr_re_dev.protocol.probe_runner import send_vendor_writes as _send

        self._session_capture.log_section(f"reference send: {label}")
        frames, ack = await _send(self._client, writes, timeout_ms=timeout_ms)
        result = "ACK" if ack else ("reply" if frames else "silent")
        self._session_capture.log_operation(
            label,
            result=result,
            writes=writes,
            frames=frames,
        )
        return frames, ack

    async def raw_write(
        self,
        char_uuid: str,
        write_hex: str,
        *,
        wait_ms: int = 2000,
    ) -> list[bytes]:
        if not self._client:
            raise RuntimeError("Not connected")
        from zephyr_re.util.hexio import parse_hex

        data = parse_hex(write_hex)
        self._session_capture.log_section(f"raw write → {char_uuid}")
        await self._client.start_notify(char_uuid)
        self._client.clear_notifications(char_uuid)
        await self._client.write(char_uuid, data, response=True)
        await asyncio.sleep(wait_ms / 1000.0)
        frames = self._client.drain_notifications(char_uuid)
        result = "reply" if frames else "silent"
        self._session_capture.log_operation(
            "raw_write",
            result=result,
            writes=[data],
            frames=frames,
        )
        return frames

    def export_capture(self, path: Path | None = None) -> Path:
        root = project_root()
        out = path or root / "research" / "captures" / f"session-{self.capture.session_id}.json"
        return self.capture.export(out)
