"""Terminal menu interface for Razer Zephyr reverse engineering."""

from __future__ import annotations

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from zephyr_re.ble.client import GattOperationTimeout
from zephyr_re.ble.scanner import (
    BleDevice,
    DeviceNotAdvertisingError,
    find_zephyr_target,
    live_connect_candidates,
    scan_devices,
)
from zephyr_re_dev.config import GattMapConfig
from zephyr_re_dev.device.state import DeviceState
from zephyr_re_dev.device.zephyr import ConnectSummary, ZephyrDevice
from zephyr_re.protocol.base import CommandResult, FanSpeed
from zephyr_re_dev.protocol.factory import BACKEND_NAMES
from zephyr_re_dev.ble.gatt_read import format_read_results
from zephyr_re_dev.protocol.hazel_write import reference_write_pairs
from zephyr_re_dev.util.frame_decode import decode_vendor_frame
from zephyr_re.util.hexio import format_hex

console = Console()


def pause(msg: str = "Press Enter to continue...") -> None:
    input(msg)


def prompt_choice(prompt: str, options: list[str], *, allow_empty: bool = False) -> int | None:
    for i, opt in enumerate(options, 1):
        console.print(f"  [{i}] {opt}")
    hint = f"Enter menu number 1–{len(options)}"
    while True:
        raw = input(f"{prompt} ({hint}): ").strip()
        if allow_empty and raw == "":
            return None
        if raw.isdigit():
            idx = int(raw)
            if 1 <= idx <= len(options):
                return idx - 1
        console.print(f"[red]Invalid — pick 1–{len(options)}[/red]")


def prompt_wave_rate() -> int | None:
    """Menu 1–5 or direct rate byte 0/6–255 (higher byte = slower)."""
    from zephyr_re_dev.protocol.hazel_write import WAVE_SPEED_PRESETS

    preset_keys = ("factory", "slow", "medium", "fast")
    console.print("[dim]Pick [1–5] or type rate byte 0 or 6–255 (e.g. 90). Higher = slower.[/dim]")
    for i, key in enumerate(preset_keys, 1):
        rate = WAVE_SPEED_PRESETS[key]
        note = {
            "factory": "device default",
            "slow": "APK minimum",
            "medium": "Hazel APK tier",
            "fast": "APK maximum",
        }[key]
        console.print(f"  [{i}] {key} = {rate} ({note})")
    console.print("  [5] custom rate byte (0–255)")
    while True:
        raw = input("Wave speed: ").strip()
        if not raw.isdigit():
            console.print("[red]Enter 1–5 or a number 0–255[/red]")
            continue
        n = int(raw)
        if 1 <= n <= 4:
            return WAVE_SPEED_PRESETS[preset_keys[n - 1]]
        if n == 5:
            custom = input("Rate byte (0–255) [90]: ").strip() or "90"
            if not custom.isdigit() or not 0 <= int(custom) <= 255:
                console.print("[red]Invalid rate byte[/red]")
                continue
            return int(custom)
        if 0 <= n <= 255:
            return n
        console.print("[red]Rate must be 0–255[/red]")


_EXTERNAL_EFFECTS: list[tuple[str, str]] = [
    ("off", "off"),
    ("static", "static — solid color"),
    ("breathing", "breathing — pulse"),
    ("spectrum", "spectrum — gradient cycle"),
    ("wave", "wave — rotating ring"),
]

_INTERNAL_EFFECTS: list[tuple[str, str]] = [
    ("off", "off"),
    ("static", "static — solid color"),
    ("breathing", "breathing — pulse"),
    ("spectrum", "spectrum — gradient cycle"),
]


_NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "r": (255, 0, 0),
    "red": (255, 0, 0),
    "g": (0, 255, 0),
    "green": (0, 255, 0),
    "b": (0, 0, 255),
    "blue": (0, 0, 255),
    "w": (255, 255, 255),
    "white": (255, 255, 255),
    "c": (0, 255, 255),
    "cyan": (0, 255, 255),
    "m": (255, 0, 255),
    "magenta": (255, 0, 255),
    "y": (255, 255, 0),
    "yellow": (255, 255, 0),
    "off": (0, 0, 0),
    "black": (0, 0, 0),
}


def parse_color_input(raw: str) -> tuple[int, int, int] | None:
    raw = raw.strip()
    if not raw:
        return None
    named = _NAMED_COLORS.get(raw.lower())
    if named is not None:
        return named
    if raw.startswith("#"):
        raw = raw[1:]
    if len(raw) == 3 and all(c in "0123456789abcdefABCDEF" for c in raw):
        return (
            int(raw[0] * 2, 16),
            int(raw[1] * 2, 16),
            int(raw[2] * 2, 16),
        )
    if len(raw) == 6 and all(c in "0123456789abcdefABCDEF" for c in raw):
        return int(raw[0:2], 16), int(raw[2:4], 16), int(raw[4:6], 16)
    parts = [p.strip() for p in raw.replace(",", " ").split()]
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        r, g, b = (int(p) for p in parts)
        if all(0 <= v <= 255 for v in (r, g, b)):
            return r, g, b
    return None


class App:
    def __init__(self) -> None:
        self.config = GattMapConfig.load()
        self.device = ZephyrDevice(backend_name="auto", config=self.config)
        self.scanned: list[BleDevice] = []

    def print_connect_success(self, summary: ConnectSummary, *, already: bool = False) -> None:
        title = "Already connected" if already else "Connected to Razer Zephyr"
        vendor = "[green]yes[/green]" if summary.vendor_gatt else "[yellow]no[/yellow]"
        battery = "[green]yes[/green]" if summary.battery_gatt else "[yellow]no[/yellow]"
        lines = [
            f"[bold green]OK[/bold green] — {'Session active' if already else 'Pairing successful'}",
            "",
            f"Device:  {summary.name or 'Razer Zephyr'}",
            f"Address: {summary.address}",
            f"Backend: {summary.backend}",
            "",
            f"GATT services:         {summary.service_count}",
            f"Characteristics:       {summary.characteristic_count}",
            f"Notify subscriptions:  {summary.notify_subscriptions}",
            f"Razer vendor service:  {vendor}",
            f"Battery service:       {battery}",
            "",
            "[dim]GATT snapshot saved to research/gatt-map.md[/dim]",
            self._session_log_hint(),
            "[cyan]Next: [1] Read all + listen  |  [2] Send reference codes[/cyan]",
        ]
        console.print(Panel("\n".join(lines), title=title, border_style="green"))

    def _session_log_hint(self) -> str:
        path = self.device.live_log_path
        if path is None:
            return "[dim]Session log: research/captures/session-*.log[/dim]"
        return f"[dim]Session log (tail -f):[/dim] [cyan]{path}[/cyan]"

    def print_connect_brief(self, summary: ConnectSummary) -> None:
        console.print(
            f"[green]Connected[/green] to {summary.name or 'Razer Zephyr'} "
            f"({summary.service_count} services, backend {summary.backend})"
        )
        console.print(self._session_log_hint())

    def header(self) -> None:
        conn = "connected" if self.device.is_connected else "disconnected"
        name = self.device.connection_info.name if self.device.connection_info else "—"
        backend = self.device.active_protocol_name if self.device.is_connected else self.device.backend_name
        log_line = ""
        if self.device.live_log_path is not None:
            log_line = f"\nLog: {self.device.live_log_path}"
        console.print(
            Panel(
                f"Status: [bold]{conn}[/bold]  |  Device: {name}  |  Backend: {backend}{log_line}",
                title="Razer Zephyr RE",
                border_style="cyan",
            )
        )

    def _print_scan_table(self, devices: list[BleDevice], *, title: str) -> None:
        if not devices:
            console.print("[yellow]No devices found.[/yellow]")
            return
        table = Table(title=title)
        table.add_column("#")
        table.add_column("Name")
        table.add_column("Address")
        table.add_column("RSSI")
        table.add_column("Source")
        table.add_column("Connect?")
        for i, d in enumerate(devices, 1):
            if d.source == "system_connected":
                connectable = "[green]system[/green]"
            elif d.is_live():
                connectable = "[green]yes[/green]"
            elif d.source == "known":
                connectable = "[yellow]saved[/yellow]"
            else:
                connectable = "[red]offline[/red]"
            table.add_row(
                str(i),
                d.name or "—",
                d.address,
                str(d.rssi) if d.rssi is not None else "—",
                d.source,
                connectable,
            )
        console.print(table)
        live = live_connect_candidates(devices, name_patterns=self.config.device_name_patterns)
        if live:
            console.print(
                f"[green]{len(live)} connectable Zephyr candidate(s)[/green]"
            )
        else:
            console.print(
                "[yellow]No connectable Zephyr found. Pair in System Settings or use pairing mode.[/yellow]"
            )
        console.print(
            "[dim]Connect? yes = advertising; system = connected in macOS Bluetooth[/dim]"
        )

    async def try_connect(self, *, quiet: bool = False, force: bool = False) -> bool:
        if (
            not force
            and self.device.is_connected
            and self.device.connection_info is not None
        ):
            if not quiet:
                summary = self.device.build_connect_summary()
                if summary:
                    self.print_connect_success(summary, already=True)
            return True

        if not quiet:
            console.print("[cyan]Looking for Razer Zephyr...[/cyan]")
            console.print(
                "[dim]Paired in System Settings or advertising on-air.[/dim]"
            )
        else:
            console.print("[dim]Connecting to Razer Zephyr...[/dim]")

        try:
            target = await find_zephyr_target(self.config.device_name_patterns)
        except DeviceNotAdvertisingError as exc:
            if quiet:
                console.print("[yellow]Zephyr not found — pair in System Settings or use [6] Reconnect[/yellow]")
            else:
                console.print(Panel(str(exc), title="Zephyr not found", border_style="yellow"))
                self.scanned = await scan_devices(
                    timeout=5.0,
                    name_patterns=self.config.device_name_patterns,
                    include_known=True,
                )
                self._print_scan_table(self.scanned, title="Diagnostic scan (includes offline)")
            return False

        self.scanned = [target]
        if not quiet:
            if target.source == "system_connected":
                found = f"[green]Found[/green] {target.name} @ {target.address} (System Bluetooth)"
            elif target.source in ("retrieved", "resolved"):
                found = f"[green]Found[/green] {target.name} @ {target.address} (paired / system GATT)"
            else:
                rssi = f"{target.rssi} dBm" if target.rssi is not None else "?"
                found = f"[green]Found[/green] {target.name} @ {target.address} (RSSI {rssi})"
            console.print(found)
            console.print("[cyan]Opening GATT session...[/cyan]")

        try:
            self.device.select_device(target)
            summary = await self.device.connect(retries=3)
            self.config = GattMapConfig.load()
            if quiet:
                self.print_connect_brief(summary)
            else:
                self.print_connect_success(summary)
            return True
        except Exception as exc:
            if quiet:
                console.print(f"[red]Connect failed:[/red] {exc}")
            else:
                console.print(
                    Panel(
                        f"[bold red]Connection failed[/bold red]\n\n{exc}\n\n"
                        "[dim]• System Settings → Bluetooth\n"
                        "• Pairing mode: mask off → hold button ~4s → blue blink\n"
                        "• Privacy & Security → Bluetooth → allow Terminal/Cursor[/dim]",
                        title="Connect failed",
                        border_style="red",
                    )
                )
            return False

    async def ensure_connected(self, *, quiet: bool = True) -> bool:
        if self.device.is_connected:
            return True
        return await self.try_connect(quiet=quiet)

    def print_command_result(self, result: CommandResult) -> None:
        if result.ok:
            console.print(f"[green]{result.message}[/green]")
        elif result.sent:
            console.print(f"[yellow]{result.message}[/yellow]")
            console.print("[dim]Command sent but firmware did not return 0x02 ACK.[/dim]")
        else:
            console.print(f"[red]{result.message}[/red]")
        if result.responses:
            for i, frame in enumerate(result.responses[:3], 1):
                console.print(f"[dim]  notify[{i}] {format_hex(frame)}[/dim]")

    def print_device_state(self, state: DeviceState) -> None:
        if state.external_color is not None:
            c = state.external_color
            color_line = f"#{c.r:02X}{c.g:02X}{c.b:02X} ({c.r}, {c.g}, {c.b})"
        elif state.external_color_note:
            color_line = f"— ({state.external_color_note})"
        else:
            color_line = "—"
        effect_line = state.external_effect or "—"
        effect_labels = {
            "off": "off",
            "static": "static (solid)",
            "breathing": "breathing (pulse)",
            "spectrum": "spectrum (gradient)",
            "wave": "wave (rotating ring)",
        }
        if state.external_effect in effect_labels:
            effect_line = effect_labels[state.external_effect]
        if state.external_brightness_percent is not None:
            raw = state.external_brightness
            bright_line = f"{state.external_brightness_percent}% (zone 0x05)"
            if raw is not None and raw > 100:
                bright_line += f", raw 0x{raw:02X}"
        elif state.external_brightness is not None:
            bright_line = f"{state.external_brightness} (zone 0x05)"
        else:
            bright_line = "—"
        if state.internal_brightness_percent is not None:
            int_bright = f"{state.internal_brightness_percent}% (zone 0x01)"
        elif state.internal_brightness is not None:
            int_bright = f"{state.internal_brightness} (zone 0x01)"
        else:
            int_bright = "—"
        fan_line = state.fan_speed.value
        fan_src = state.fan_speed_source
        if fan_src not in ("assumed",):
            fan_line += f" ({fan_src})"
        fw_line = state.firmware_version or "—"
        charge_line = (
            "yes" if state.is_charging else "no" if state.is_charging is not None else "—"
        )
        internal_effect_line = state.internal_effect or "—"
        lines = [
            f"Battery:         {state.battery_percent}%" if state.battery_percent is not None else "Battery:         —",
            f"Ext brightness:  {bright_line}",
            f"Int brightness:  {int_bright}",
            f"External color:  {color_line}",
            f"External effect: {effect_line}",
            f"Internal effect: {internal_effect_line}",
            f"Fans:            {fan_line}",
            f"Internal light:  {state.internal_light}",
            f"Firmware:        {fw_line}",
            f"Charging:        {charge_line}",
        ]
        console.print(Panel("\n".join(lines), title="Device state", border_style="green"))

    async def sync_device_state(self) -> None:
        """Read full device state, then listen 30s."""
        if not await self.ensure_connected():
            return
        d = self.device
        d.capture.log_section("sync: Read all + listen (30s)")
        state = await self._run_control(d.fetch_device_state(), "Read device state", timeout=90.0)
        if state is None:
            return
        for line in format_read_results(state.gatt_reads):
            console.print(line)
        d.capture.log_read_batch(state.gatt_reads)
        d.capture.log_device_state(state)
        self.print_device_state(state)
        path = d.append_read_snapshot(state.gatt_reads)
        console.print(f"[dim]Saved to {path}[/dim]")
        duration = 30.0
        console.print("\n[cyan]Listening 30s — press mask button, change modes, etc.[/cyan]")
        captures = await self._run_control(
            d.listen_notifications(duration),
            "Listen",
            timeout=duration + 15.0,
        )
        if captures is None:
            return
        d.capture.log_listen_summary(captures)
        d.apply_listen_to_state(captures)
        if d.last_state is not None:
            d.capture.log_section("device state after listen")
            d.capture.log_device_state(d.last_state)
            console.print("\n[bold]Updated state after listen:[/bold]")
            self.print_device_state(d.last_state)
        if not captures:
            console.print("[yellow]No notifications received[/yellow]")
        for cap in captures:
            console.print(f"[bold]{cap.char_uuid}[/bold] ({len(cap.frames)} frames)")
            for i, frame in enumerate(cap.frames[:20], 1):
                console.print(f"  [{i}] {format_hex(frame)}")
            if len(cap.frames) > 20:
                console.print(f"  … +{len(cap.frames) - 20} more")

    async def menu_control(self) -> None:
        if not await self.ensure_connected():
            return
        console.print(
            "[dim]Sync from main [1] first. External = zone 0x05 (rings). Internal = zone 0x01 (mouth).[/dim]"
        )
        while self.device.is_connected:
            self.header()
            options = [
                "Read: vendor key probe (legacy mouse keys)",
                "Read: battery",
                "Read: external zone (color / effect)",
                "Write external: static color",
                "Write external: brightness",
                "Write external: effect (off / static / breathing / spectrum / wave)",
                "Write internal: static color",
                "Write internal: brightness",
                "Write internal: effect (off / static / breathing / spectrum)",
                "Write internal: off (shortcut)",
                "Write fans: off / low / high",
                "Probe: external static effect variants",
                "Probe: static then color",
                "Probe: external color variants",
                "Probe: internal light variants",
                "Probe: fan write variants",
                "Probe: firmware effect wire IDs 0–15 (watch LEDs + read-back)",
                "Probe: Hazel extras (brightness, breathing, starlight, timeout)",
                "Back to main menu",
            ]
            idx = prompt_choice("Device control:", options)
            if idx is None or idx == 18:
                break
            await self._handle_control(idx)

    def _print_probe_attempt(self, attempt, index: int, total: int) -> None:
        writes = " | ".join(format_hex(w) for w in attempt.writes)
        if attempt.ack:
            status = "[green]ACK[/green]"
        elif attempt.any_reply:
            rejected = any(
                len(f) >= 8 and f[7] == 0x03 for f in attempt.frames
            )
            status = "[red]rejected 0x03[/red]" if rejected else "[yellow]reply[/yellow]"
        else:
            status = "[dim]silent[/dim]"
        console.print(f"  [{index}/{total}] {attempt.name}: {status}  sent {writes}")
        for i, frame in enumerate(attempt.frames[:2], 1):
            console.print(f"         notify[{i}] {format_hex(frame)}")

    async def _run_control(self, coro, label: str, *, timeout: float = 12.0):
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            console.print(f"[red]{label} timed out — try Reconnect from main menu[/red]")
            return None
        except GattOperationTimeout as exc:
            console.print(f"[red]{exc}[/red]")
            return None

    _CONTROL_LABELS: dict[int, str] = {
        0: "Vendor read probe",
        1: "Read battery",
        2: "Read external zone",
        3: "Write external color",
        4: "Write external brightness",
        5: "Write external effect",
        6: "Write internal color",
        7: "Write internal brightness",
        8: "Write internal effect",
        9: "Write internal off",
        10: "Write fan speed",
        11: "Probe static writes",
        12: "Probe static→color writes",
        13: "Probe color writes",
        14: "Probe internal light writes",
        15: "Probe fan writes",
        16: "Probe firmware effect wire IDs",
        17: "Probe Hazel extras",
    }

    async def _pick_zone_effect(
        self,
        zone_label: str,
        *,
        include_wave: bool,
    ) -> tuple[str, dict[str, object]] | None:
        effects = _EXTERNAL_EFFECTS if include_wave else _INTERNAL_EFFECTS
        labels = [f"{name} — {desc}" for name, desc in effects]
        eidx = prompt_choice(f"Effect on {zone_label}:", labels)
        if eidx is None:
            return None
        effect_name, _ = effects[eidx]
        opts: dict[str, object] = {}
        if effect_name == "static":
            default = "blue" if include_wave else "green"
            raw = input(f"Color ({default}, #RRGGBB, R,G,B) [{default}]: ").strip() or default
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return None
            opts["r"], opts["g"], opts["b"] = rgb
        elif effect_name == "wave":
            rate = prompt_wave_rate()
            if rate is None:
                return None
            opts["wave_rate"] = rate
        return effect_name, opts

    async def _handle_control(self, idx: int) -> None:
        d = self.device
        label = self._CONTROL_LABELS.get(idx)
        if label:
            d.capture.log_section(f"control: {label}")
        if idx == 0:
            console.print("[cyan]Vendor READ keys (write → notify reply)...[/cyan]")
            attempts = await self._run_control(
                d.probe_vendor_reads(on_attempt=self._print_probe_attempt),
                "Vendor reads",
                timeout=30.0,
            )
            if attempts is None:
                pause()
                return
            if not attempts:
                console.print("[yellow]No vendor read candidates configured[/yellow]")
            else:
                acked = [a for a in attempts if a.ack]
                replied = [a for a in attempts if a.any_reply and not a.ack]
                console.print(
                    f"[dim]{len(acked)} acked, {len(replied)} replied, "
                    f"{len(attempts) - len(acked) - len(replied)} silent[/dim]"
                )
        elif idx == 1:
            info = await self._run_control(d.read_battery(), "Battery read")
            if info is None:
                pause()
                return
            if info and info.percent is not None:
                console.print(f"[green]Battery: {info.percent}%[/green]")
            else:
                console.print(f"[yellow]{info.message if info else 'No data'}[/yellow]")
        elif idx == 2:
            color = await self._run_control(d.read_external_color(), "Read color")
            if color:
                console.print(
                    f"[green]RGB({color.r}, {color.g}, {color.b}) "
                    f"#{color.r:02X}{color.g:02X}{color.b:02X}[/green]"
                )
            else:
                console.print("[yellow]Could not read color[/yellow]")
        elif idx == 3:
            raw = input("External color (blue, #0000FF, R,G,B): ").strip()
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return
            r = await self._run_control(d.set_external_color(*rgb), "Set external color")
            if r is not None:
                self.print_command_result(r)
        elif idx == 4:
            raw = input("External brightness (0–255): ").strip()
            if not raw.isdigit():
                console.print("[red]Invalid brightness[/red]")
                return
            r = await self._run_control(d.set_external_brightness(int(raw)), "Set external brightness")
            if r is not None:
                self.print_command_result(r)
        elif idx == 5:
            picked = await self._pick_zone_effect("external zone 0x05", include_wave=True)
            if picked is None:
                return
            effect_name, opts = picked
            r = await self._run_control(
                d.set_external_effect(effect_name, **opts),
                f"Set external effect {effect_name}",
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 6:
            raw = input("Internal color (green, #00FF00, R,G,B) [green]: ").strip() or "green"
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return
            r = await self._run_control(
                d.set_internal_light(True, *rgb),
                "Set internal color",
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 7:
            raw = input("Internal brightness (0–255): ").strip()
            if not raw.isdigit():
                console.print("[red]Invalid brightness[/red]")
                return
            r = await self._run_control(d.set_internal_brightness(int(raw)), "Set internal brightness")
            if r is not None:
                self.print_command_result(r)
        elif idx == 8:
            picked = await self._pick_zone_effect("internal zone 0x01", include_wave=False)
            if picked is None:
                return
            effect_name, opts = picked
            r = await self._run_control(
                d.set_internal_effect(effect_name, **opts),
                f"Set internal effect {effect_name}",
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 9:
            r = await self._run_control(d.set_internal_light(False), "Set internal off")
            if r is not None:
                self.print_command_result(r)
        elif idx == 10:
            sub = prompt_choice(
                "Fan speed:",
                ["off", "low", "high"],
            )
            if sub is None:
                return
            speeds = (FanSpeed.OFF, FanSpeed.LOW, FanSpeed.HIGH)
            r = await self._run_control(d.set_fan_speed(speeds[sub]), "Set fan speed")
            if r is not None:
                self.print_command_result(r)
        elif idx == 11:
            r = await self._run_control(
                d.probe_static_effect(on_attempt=self._print_probe_attempt),
                "Static effect probe",
                timeout=60.0,
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 12:
            raw = input("Color after static mode (blue, #0000FF, R,G,B): ").strip()
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return
            r = await self._run_control(
                d.probe_static_then_color(*rgb, on_attempt=self._print_probe_attempt),
                "Static-then-color probe",
                timeout=90.0,
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 13:
            raw = input("Color to probe (blue, #0000FF, R,G,B): ").strip()
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return
            r = await self._run_control(
                d.probe_external_color(*rgb, on_attempt=self._print_probe_attempt),
                "Color probe",
                timeout=60.0,
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 14:
            raw = input("Internal color to probe (green, #00FF00, R,G,B): ").strip() or "green"
            rgb = parse_color_input(raw)
            if rgb is None:
                console.print("[red]Invalid color[/red]")
                return
            r = await self._run_control(
                d.probe_internal_light_writes(*rgb, on_attempt=self._print_probe_attempt),
                "Internal light probe",
                timeout=60.0,
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 15:
            sub = prompt_choice("Fan level to probe:", ["off (0)", "low (1)", "high (2)"])
            if sub is None:
                return
            r = await self._run_control(
                d.probe_fan_writes(sub, on_attempt=self._print_probe_attempt),
                "Fan probe",
                timeout=60.0,
            )
            if r is not None:
                self.print_command_result(r)
        elif idx == 17:
            console.print(
                "[dim]Starlight = random LED sparkles. Breathing tests 1–2 colors. "
                "Ends with 30s timeout probes (chroma 0x0B + Hazel A7 raw 30). "
                "If either ACKs, LEDs may auto-off — you will be prompted to wait, then restore never.[/dim]"
            )
            r = await self._run_control(
                d.probe_hazel_extras(on_attempt=self._print_probe_attempt),
                "Hazel extras probe",
                timeout=180.0,
            )
            if r is not None:
                self.print_command_result(r)
            if r is not None and "rejected" in (r.message or "").lower():
                console.print(
                    "[dim]Starlight and timeout probes returned 0x03 — firmware does not accept them. "
                    "Skip wait/restore.[/dim]"
                )
            else:
                console.print(
                    "[yellow]If a timeout probe ACKed, watch whether LEDs turn off on their own.[/yellow]"
                )
                wait = input("Wait 35s to observe timeout? [y/N]: ").strip().lower()
                if wait == "y":
                    console.print("[dim]Waiting 35s…[/dim]")
                    await asyncio.sleep(35)
                rr = await self._run_control(d.restore_hazel_led_timeout(), "Restore LED timeout (never)")
                if rr is not None:
                    self.print_command_result(rr)
        elif idx == 16:
            zone_pick = prompt_choice(
                "Sweep firmware effect wire IDs on:",
                ["external zone 0x05 (fan rings)", "internal zone 0x01 (mouth)"],
            )
            if zone_pick is None:
                return
            from zephyr_re_dev.protocol.zephyr_parse import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE

            zone = EXTERNAL_LIGHT_ZONE if zone_pick == 0 else INTERNAL_LIGHT_ZONE
            raw = input("ID range end (0–15) [15]: ").strip() or "15"
            id_end = int(raw) if raw.isdigit() and 0 <= int(raw) <= 15 else 15
            console.print(
                "[dim]Sends minimal payload per wire ID, then reads zone back. "
                "ACK 0x02 = accepted; read-back shows what firmware stored. "
                "Watch the mask — ACK alone does not prove a visible effect.[/dim]"
            )
            r = await self._run_control(
                d.probe_firmware_effect_ids(zone, id_end=id_end, on_attempt=self._print_probe_attempt),
                "Effect ID sweep",
                timeout=120.0,
            )
            if r is not None:
                self.print_command_result(r)
        pause()

    async def menu_gatt_explorer(self) -> None:
        if not await self.ensure_connected():
            return
        services = self.device.enumerate_gatt()
        if not services:
            console.print("[yellow]No GATT services.[/yellow]")
            return
        char_list: list[tuple[str, str, list[str]]] = []
        for svc in services:
            console.print(f"\n[bold cyan]Service[/bold cyan] {svc.uuid}")
            for char in svc.characteristics:
                props = ", ".join(char.properties)
                console.print(f"  {char.uuid}  handle={char.handle}  [{props}]")
                char_list.append((svc.uuid, char.uuid, char.properties))
        if input("\nRead all readable characteristics now? [Y/n]: ").strip().lower() != "n":
            self.device.capture.log_section("GATT explorer: read all")
            results = await self.device.read_all_gatt()
            for line in format_read_results(results):
                console.print(line)
            path = self.device.append_read_snapshot(results)
            console.print(f"[dim]Saved to {path}[/dim]")
        console.print("\n[dim]Copy service/write/notify UUIDs into tools/config/gatt_map.yaml[/dim]")
        if self.config.write_char_uuid is None and char_list:
            writable = [c for _, c, p in char_list if "write" in p]
            notify = [c for _, c, p in char_list if "notify" in p]
            if writable:
                console.print(f"[dim]Writable chars: {', '.join(writable[:5])}[/dim]")
            if notify:
                console.print(f"[dim]Notify chars: {', '.join(notify[:5])}[/dim]")

    async def _send_reference_pair(
        self,
        index: int,
        *,
        req_base: int = 0x40,
    ) -> bool:
        """Send one reference command; return True if notify status was 0x02."""
        fresh = reference_write_pairs(req_base)[index]
        console.print(f"\n[bold cyan]{fresh.name}[/bold cyan]")
        console.print(f"  write[1] [yellow]{format_hex(fresh.header)}[/yellow]")
        console.print(f"  write[2] [yellow]{format_hex(fresh.payload)}[/yellow]")
        frames, ack = await self.device.send_vendor_writes(fresh.name, fresh.writes)
        if frames:
            for i, frame in enumerate(frames, 1):
                tag = "[green]ACK 0x02[/green]" if len(frame) >= 8 and frame[7] == 0x02 else "[dim]reply[/dim]"
                console.print(f"  notify[{i}] {tag} {format_hex(frame)}")
                console.print(f"           [dim]{decode_vendor_frame(frame)}[/dim]")
        else:
            console.print("  [yellow]No notify reply[/yellow]")
        if ack:
            console.print("  [green]Firmware accepted (same check as Hazel app).[/green]")
        else:
            console.print("  [yellow]No 0x02 ACK — command may not have applied.[/yellow]")
        self.device.capture.log(
            "info",
            message=f"reference_send {fresh.name}: protocol_ack={ack}",
        )
        return ack

    async def menu_send_reference_codes(self) -> None:
        """Send Hazel reference writes one at a time (ACK = accepted)."""
        if not await self.ensure_connected():
            return
        if not self.device.vendor_available:
            console.print("[yellow]Razer vendor GATT not available on this connection.[/yellow]")
            return
        pairs = reference_write_pairs()
        console.print(
            "[dim]Sends immediately on pick. Notify byte 7 = 0x02 means firmware accepted. "
            "Rotating ring = [1] wave (factory rate 90). Gradient = [2] spectrum. "
            "Pulse = [3] breathing. Higher rate byte = slower wave.[/dim]\n"
        )
        options = [p.name for p in pairs] + ["Run all (pause between)", "Back"]
        while True:
            idx = prompt_choice("Send reference code:", options)
            if idx is None or idx == len(options) - 1:
                return
            self.device.capture.log_section("reference codes")
            if idx == len(options) - 2:
                for i in range(len(pairs)):
                    await self._send_reference_pair(i, req_base=0x40)
                    if i < len(pairs) - 1:
                        input("\nPress Enter for next command...")
                return
            await self._send_reference_pair(idx, req_base=0x40)

    async def menu_raw_probe(self) -> None:
        if not await self.ensure_connected():
            return
        services = self.device.enumerate_gatt()
        chars: list[tuple[str, list[str]]] = []
        for svc in services:
            for char in svc.characteristics:
                if "write" in char.properties:
                    chars.append((char.uuid, char.properties))
        if not chars:
            console.print("[yellow]No writable characteristics.[/yellow]")
            return
        idx = prompt_choice("Write to characteristic:", [f"{u} [{', '.join(p)}]" for u, p in chars])
        if idx is None:
            return
        char_uuid = chars[idx][0]
        hex_str = input("Hex bytes (space-separated): ").strip()
        if not hex_str:
            return
        wait_raw = input("Wait for notifies (ms) [2000]: ").strip() or "2000"
        wait_ms = int(wait_raw) if wait_raw.isdigit() else 2000
        try:
            frames = await self.device.raw_write(char_uuid, hex_str, wait_ms=wait_ms)
            if frames:
                console.print("[green]Notifications:[/green]")
                for i, frame in enumerate(frames, 1):
                    console.print(f"  [{i}] {format_hex(frame)}")
            else:
                console.print("[yellow]No notifications received[/yellow]")
        except Exception as exc:
            console.print(f"[red]Error: {exc}[/red]")

    def menu_backend(self) -> None:
        current = self.device.backend_name
        console.print(f"Current backend setting: [bold]{current}[/bold]")
        if self.device.is_connected:
            console.print(f"Active protocol: [bold]{self.device.active_protocol_name}[/bold]")
        options = list(BACKEND_NAMES)
        idx = prompt_choice("Select backend:", options)
        if idx is None:
            return
        name = options[idx]
        self.device.set_backend(name)
        self.config = GattMapConfig.load()
        console.print(f"[green]Backend set to {name}[/green]")
        if self.device.is_connected:
            console.print("[dim]Reconnect to apply backend on_connect logic.[/dim]")

    def menu_session_log(self) -> None:
        path = self.device.live_log_path
        if path is not None:
            console.print(f"[bold]Live log[/bold] (appends continuously): [cyan]{path}[/cyan]")
            console.print(f"[dim]In another terminal: tail -f {path}[/dim]\n")
        lines = self.device.capture.live_tail(50)
        if not lines:
            lines = self.device.capture.summary_lines(40)
        if not lines:
            console.print("[yellow]No session log entries yet.[/yellow]")
            return
        for line in lines:
            if line.startswith("#"):
                console.print(f"[dim]{line}[/dim]")
            elif "OPERATION" in line or "→" in line:
                console.print(f"[cyan]{line}[/cyan]")
            elif "NOTIFY" in line:
                console.print(f"[green]{line}[/green]")
            elif "WRITE" in line:
                console.print(f"[yellow]{line}[/yellow]")
            else:
                console.print(line)
        if input("\nExport JSON snapshot to research/captures/? [y/N]: ").strip().lower() == "y":
            out = self.device.export_capture()
            console.print(f"[green]Exported to {out}[/green]")
            console.print(f"[dim]Human-readable log remains at {path}[/dim]")

    async def run(self) -> None:
        await self.try_connect(quiet=True)
        while True:
            self.header()
            options = [
                "Read all + listen (30s)",
                "Send reference codes",
                "Device control",
                "GATT explorer",
                "Raw hex probe",
                "Protocol / backend",
                "Show session log",
                "Reconnect",
                "Disconnect",
                "Quit",
            ]
            idx = prompt_choice("Main menu:", options)
            if idx is None:
                continue
            if idx == 0:
                await self.sync_device_state()
            elif idx == 1:
                await self.menu_send_reference_codes()
            elif idx == 2:
                await self.menu_control()
            elif idx == 3:
                await self.menu_gatt_explorer()
            elif idx == 4:
                await self.menu_raw_probe()
            elif idx == 5:
                self.menu_backend()
            elif idx == 6:
                self.menu_session_log()
            elif idx == 7:
                if self.device.is_connected:
                    await self.device.disconnect()
                await self.try_connect(quiet=False, force=True)
            elif idx == 8:
                if self.device.is_connected:
                    await self.device.disconnect()
                    console.print("[green]Disconnected.[/green]")
                else:
                    console.print("[yellow]Not connected.[/yellow]")
            elif idx == 9:
                if self.device.is_connected:
                    await self.device.disconnect()
                break
            pause()


def main() -> None:
    app = App()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    main()
