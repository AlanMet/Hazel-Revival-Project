"""Simple terminal UI — Hazel app features only."""

from __future__ import annotations

import asyncio
import sys

from rich.console import Console

from zephyr_re.protocol.base import CommandStatus
from zephyr_re.protocol.packets import WAVE_RATE_FACTORY, WAVE_SPEED_PRESETS
from zephyr_re.zephyr import Zephyr

console = Console()


def pause() -> None:
    input("Press Enter...")


def pick(prompt: str, options: list[str]) -> int | None:
    for i, opt in enumerate(options, 1):
        console.print(f"  [{i}] {opt}")
    while True:
        raw = input(f"{prompt} (1–{len(options)}): ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(options):
            return int(raw) - 1
        console.print("[red]Invalid choice[/red]")


def pick_rgb(label: str) -> tuple[int, int, int]:
    while True:
        raw = input(f"{label} RGB (r g b, 0–255): ").strip()
        parts = raw.split()
        if len(parts) == 3 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
            return int(parts[0]), int(parts[1]), int(parts[2])
        console.print("[red]Enter three numbers, e.g. 255 0 0[/red]")


def pick_breathing_colors() -> dict[str, int | None]:
    mode = pick("Breathing colours:", ["single", "bi-colour", "default (no colour)"])
    if mode == 2:
        return {"r": 0, "g": 0, "b": 0, "r2": None, "g2": None, "b2": None}
    r, g, b = pick_rgb("Colour 1")
    if mode == 0:
        return {"r": r, "g": g, "b": b, "r2": None, "g2": None, "b2": None}
    r2, g2, b2 = pick_rgb("Colour 2")
    return {"r": r, "g": g, "b": b, "r2": r2, "g2": g2, "b2": b2}


def show_result(result) -> None:
    colour = "green" if result.status == CommandStatus.OK else "yellow"
    console.print(f"[{colour}]{result.message}[/{colour}]")


class TerminalApp:
    def __init__(self) -> None:
        self.zephyr = Zephyr()

    async def ensure_connected(self) -> bool:
        if self.zephyr.is_connected:
            return True
        try:
            addr = await self.zephyr.connect()
            console.print(f"[green]Connected[/green] {addr}")
            return True
        except Exception as exc:
            console.print(f"[red]Connect failed: {exc}[/red]")
            return False

    async def menu_fan(self) -> None:
        idx = pick("Fan speed:", ["Low", "High", "Off"])
        if idx is None:
            return
        fn = (self.zephyr.fan_low, self.zephyr.fan_high, self.zephyr.fan_off)[idx]
        show_result(await fn())

    async def menu_internal(self) -> None:
        idx = pick(
            "Internal lighting:",
            ["Static", "Spectrum", "Breathing", "Off"],
        )
        if idx is None:
            return
        if idx == 0:
            r, g, b = pick_rgb("Static")
            show_result(await self.zephyr.internal_static(r, g, b))
        elif idx == 1:
            show_result(await self.zephyr.internal_spectrum())
        elif idx == 2:
            show_result(await self.zephyr.internal_breathing(**pick_breathing_colors()))
        else:
            show_result(await self.zephyr.internal_off())

    async def menu_external(self) -> None:
        idx = pick(
            "External lighting:",
            ["Static", "Spectrum", "Breathing", "Wave", "Off"],
        )
        if idx is None:
            return
        if idx == 0:
            r, g, b = pick_rgb("Static")
            show_result(await self.zephyr.external_static(r, g, b))
        elif idx == 1:
            show_result(await self.zephyr.external_spectrum())
        elif idx == 2:
            show_result(await self.zephyr.external_breathing(**pick_breathing_colors()))
        elif idx == 3:
            ltr = pick("Wave direction:", ["Left → right", "Right → left"]) == 0
            speed_idx = pick(
                "Wave speed:",
                [
                    f"factory ({WAVE_RATE_FACTORY})",
                    f"slow ({WAVE_SPEED_PRESETS['slow']})",
                    f"medium ({WAVE_SPEED_PRESETS['medium']})",
                    f"fast ({WAVE_SPEED_PRESETS['fast']})",
                ],
            )
            rates = (
                WAVE_RATE_FACTORY,
                WAVE_SPEED_PRESETS["slow"],
                WAVE_SPEED_PRESETS["medium"],
                WAVE_SPEED_PRESETS["fast"],
            )
            rate = rates[speed_idx or 0]
            show_result(await self.zephyr.external_wave(left_to_right=ltr, rate=rate))
        else:
            show_result(await self.zephyr.external_off())

    async def run(self) -> None:
        console.print("[bold]Razer Zephyr[/bold] — terminal control\n")
        await self.ensure_connected()
        while True:
            status = f"connected {self.zephyr.connector.address}" if self.zephyr.is_connected else "not connected"
            console.print(f"\n[dim]{status}[/dim]")
            idx = pick(
                "Main menu:",
                [
                    "Fan speed",
                    "Internal lighting",
                    "External lighting",
                    "Reconnect",
                    "Quit",
                ],
            )
            if idx == 0:
                await self.menu_fan()
            elif idx == 1:
                await self.menu_internal()
            elif idx == 2:
                await self.menu_external()
            elif idx == 3:
                if self.zephyr.is_connected:
                    await self.zephyr.disconnect()
                await self.ensure_connected()
            elif idx == 4:
                if self.zephyr.is_connected:
                    await self.zephyr.disconnect()
                break
            pause()


def main() -> None:
    try:
        asyncio.run(TerminalApp().run())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(0)
