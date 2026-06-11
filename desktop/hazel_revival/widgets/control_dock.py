"""Zone control dock — fan / internal / external panels."""

from __future__ import annotations

import tkinter.colorchooser as colorchooser
from collections.abc import Callable

import customtkinter as ctk

from hazel_revival import theme as T
from zephyr_re.protocol.packets import WAVE_RATE_FAST, WAVE_RATE_MEDIUM, WAVE_RATE_SLOW

ZONE_TITLES = {
    "fan": "Fan speed",
    "internal": "Internal lighting",
    "external": "External lighting",
}


class ControlDock(ctk.CTkFrame):
    def __init__(
        self,
        master,
        *,
        device: DeviceController,
        worker,
        on_status: Callable[[str], None],
        on_close,
        **kwargs,
    ) -> None:
        super().__init__(master, fg_color=T.SURFACE, corner_radius=16, **kwargs)
        self.device = device
        self.worker = worker
        self.on_status = on_status
        self._on_close = on_close
        self._zone: str | None = None
        self._active_chip: ctk.CTkButton | None = None
        self._chips: list[ctk.CTkButton] = []
        self._submenu_frame: ctk.CTkFrame | None = None
        self._color_after: str | None = None
        self._pending_color = (255, 255, 255)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(14, 10))
        self.title = ctk.CTkLabel(head, text="", font=T.DISPLAY_SM, text_color=T.TEXT)
        self.title.pack(side="left")
        ctk.CTkButton(
            head,
            text="×",
            width=32,
            height=32,
            fg_color="transparent",
            hover_color="#ffffff15",
            text_color=T.MUTED,
            command=self.close,
        ).pack(side="right")

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    def open_zone(self, zone: str) -> None:
        self._zone = zone
        self.title.configure(text=ZONE_TITLES.get(zone, zone))
        for w in self.body.winfo_children():
            w.destroy()
        self._chips.clear()
        self._active_chip = None
        self._submenu_frame = None

        chips = ctk.CTkFrame(self.body, fg_color="transparent")
        chips.pack(fill="x")

        if zone == "fan":
            for label, action in (("Low", "fan_low"), ("High", "fan_high"), ("Off", "fan_off")):
                self._add_chip(chips, label, lambda a=action: self._run(a))
        elif zone == "internal":
            self._add_chip(chips, "Static", lambda: self._show_color("internal_static"))
            self._add_chip(chips, "Spectrum", lambda: self._run("internal_spectrum"))
            self._add_chip(chips, "Breathing", lambda: self._run("internal_breathing"))
            self._add_chip(chips, "Off", lambda: self._run("internal_off"))
        elif zone == "external":
            self._add_chip(chips, "Static", lambda: self._show_color("external_static"))
            self._add_chip(chips, "Spectrum", lambda: self._run("external_spectrum"))
            self._add_chip(chips, "Breathing", lambda: self._run("external_breathing"))
            self._add_chip(chips, "Wave", lambda: self._show_wave())
            self._add_chip(chips, "Off", lambda: self._run("external_off"))

        self.pack(fill="x", pady=(0, 12))

    def close(self) -> None:
        self.pack_forget()
        self._zone = None
        self._on_close()

    def _add_chip(self, parent, label: str, command) -> None:
        btn = ctk.CTkButton(
            parent,
            text=label,
            fg_color="#ffffff08",
            hover_color="#ffffff12",
            border_width=1,
            border_color=T.BORDER,
            text_color=T.TEXT,
            font=T.FONT_SM,
            height=34,
            width=80,
        )
        btn.configure(command=lambda cmd=command, b=btn: self._chip_click(cmd, b))
        btn.pack(side="left", padx=(0, 6), pady=4)
        self._chips.append(btn)

    def _chip_click(self, command, btn: ctk.CTkButton) -> None:
        if self._active_chip and self._active_chip is not btn:
            self._style_chip(self._active_chip, active=False)
        self._active_chip = btn
        self._style_chip(btn, active=True)
        command()

    def _style_chip(self, btn: ctk.CTkButton, *, active: bool) -> None:
        if active:
            btn.configure(fg_color=T.ACCENT, hover_color=T.ACCENT, text_color="#0a0a0a", border_color=T.ACCENT)
        else:
            btn.configure(
                fg_color="#ffffff08",
                hover_color="#ffffff12",
                text_color=T.TEXT,
                border_color=T.BORDER,
            )

    def _clear_submenu(self) -> None:
        if self._submenu_frame:
            self._submenu_frame.destroy()
            self._submenu_frame = None

    def _show_color(self, action: str) -> None:
        self._clear_submenu()
        self._submenu_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self._submenu_frame.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(
            self._submenu_frame,
            text="COLOUR",
            text_color=T.MUTED,
            font=T.FONT_XS,
        ).pack(anchor="w")

        row = ctk.CTkFrame(self._submenu_frame, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))

        self._color_preview = ctk.CTkFrame(row, width=48, height=48, fg_color="#ffffff", corner_radius=8)
        self._color_preview.pack(side="left")

        ctk.CTkButton(
            row,
            text="Pick colour…",
            command=lambda: self._pick_color(action),
            fg_color="#ffffff08",
            hover_color="#ffffff12",
            border_width=1,
            border_color=T.BORDER,
            text_color=T.TEXT,
        ).pack(side="left", padx=(12, 0))

        self._send_color(action, *self._pending_color)

    def _pick_color(self, action: str) -> None:
        rgb, _hex = colorchooser.askcolor(color=f"#{self._pending_color[0]:02x}{self._pending_color[1]:02x}{self._pending_color[2]:02x}")
        if rgb:
            self._pending_color = (int(rgb[0]), int(rgb[1]), int(rgb[2]))
            self._color_preview.configure(fg_color=_hex)
            self._send_color(action, *self._pending_color)

    def _send_color(self, action: str, r: int, g: int, b: int) -> None:
        if self._color_after:
            self.after_cancel(self._color_after)

        def fire() -> None:
            self._run(action, r, g, b, silent=True)

        self._color_after = self.after(180, fire)

    def _show_wave(self) -> None:
        self._clear_submenu()
        self._submenu_frame = ctk.CTkFrame(self.body, fg_color="transparent")
        self._submenu_frame.pack(fill="x", pady=(12, 0))

        ctk.CTkLabel(
            self._submenu_frame,
            text="WAVE SPEED",
            text_color=T.MUTED,
            font=T.FONT_XS,
        ).pack(anchor="w")

        row = ctk.CTkFrame(self._submenu_frame, fg_color="transparent")
        row.pack(fill="x", pady=(8, 0))

        for label, rate in (("Fast", WAVE_RATE_FAST), ("Medium", WAVE_RATE_MEDIUM), ("Slow", WAVE_RATE_SLOW)):
            ctk.CTkButton(
                row,
                text=label,
                command=lambda r=rate: self._run("external_wave", r),
                fg_color="#ffffff08",
                hover_color="#ffffff12",
                border_width=1,
                border_color=T.BORDER,
                text_color=T.TEXT,
                font=T.FONT_SM,
                height=34,
                width=80,
            ).pack(side="left", padx=(0, 6))

    def _run(self, action: str, *args, silent: bool = False) -> None:
        if not silent:
            self.on_status("Sending…")
            for btn in self._chips:
                btn.configure(state="disabled")

        async def coro():
            method = getattr(self.device, action)
            return await method(*args)

        def done(result: dict) -> None:
            if not silent:
                self.on_status(result.get("message", ""))
            for btn in self._chips:
                btn.configure(state="normal")

        def err(exc: BaseException) -> None:
            self.on_status(str(exc))
            for btn in self._chips:
                btn.configure(state="normal")

        self.worker.submit(coro(), on_success=done, on_error=err)
