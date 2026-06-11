"""Hazel Revival desktop application."""

from __future__ import annotations

import customtkinter as ctk

from hazel_revival import theme as T
from hazel_revival.async_worker import AsyncWorker
from hazel_revival.device import DeviceController
from hazel_revival.version import APP_VERSION
from hazel_revival.widgets.control_dock import ControlDock
from hazel_revival.widgets.mask_view import MaskView
from hazel_revival.widgets.onboarding import OnboardingView


class HazelRevivalApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"Hazel Revival — Razer Zephyr")
        self.geometry(f"{T.MAX_WIDTH + 40}x920")
        self.minsize(T.MAX_WIDTH, 700)
        self.configure(fg_color=T.BG)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("green")

        self.worker = AsyncWorker()
        self.device = DeviceController()

        self._build_header()
        self._build_onboarding()
        self._build_control()
        self._show_onboarding()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build_footer()

    def _build_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(24, 8))

        ctk.CTkLabel(
            header,
            text="REVERSE ENGINEERED REPLACEMENT FOR ZEPHYR",
            text_color=T.ACCENT,
            font=("Inter", 10, "bold"),
        ).pack()
        ctk.CTkLabel(header, text="Hazel Revival", font=T.DISPLAY, text_color=T.TEXT).pack(pady=(4, 0))
        ctk.CTkLabel(
            header,
            text="Control fan speed and lighting of Razer Zephyr from your computer.",
            text_color=T.MUTED,
            font=T.FONT_SM,
            wraplength=T.MAX_WIDTH,
        ).pack(pady=(6, 0))

    def _build_onboarding(self) -> None:
        self.onboarding = OnboardingView(
            self,
            on_continue=lambda: None,
            on_connect=self._connect,
        )
        self.onboarding.pack(fill="x", padx=20, pady=8)

    def _build_control(self) -> None:
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")

        top = ctk.CTkFrame(self.control_frame, fg_color="transparent")
        top.pack(fill="x", pady=(0, 8))

        pill = ctk.CTkFrame(top, fg_color=T.ACCENT_DIM, corner_radius=999, border_width=1, border_color="#44d62c40")
        pill.pack(side="left")
        dot = ctk.CTkFrame(pill, width=8, height=8, fg_color=T.ACCENT, corner_radius=999)
        dot.pack(side="left", padx=(12, 6), pady=8)
        dot.pack_propagate(False)
        self.device_name = ctk.CTkLabel(pill, text="Razer Zephyr", text_color=T.TEXT, font=T.FONT_SM)
        self.device_name.pack(side="left", padx=(0, 12), pady=8)

        ctk.CTkButton(
            top,
            text="Disconnect",
            command=self._disconnect,
            fg_color="transparent",
            hover_color="#ffffff10",
            border_width=1,
            border_color=T.BORDER,
            text_color=T.MUTED,
            width=100,
        ).pack(side="right")

        ctk.CTkLabel(
            self.control_frame,
            text="Tap a ring or zone on the mask to open controls.",
            text_color=T.MUTED,
            font=T.FONT_SM,
        ).pack(pady=(0, 8))

        self.mask = MaskView(self.control_frame, on_zone=self._open_zone)
        self.mask.pack()

        self.dock = ControlDock(
            self.control_frame,
            device=self.device,
            worker=self.worker,
            on_status=self._set_control_status,
            on_close=self._dock_closed,
        )

        self.control_status = ctk.CTkLabel(
            self.control_frame,
            text="",
            text_color=T.MUTED,
            font=T.FONT_SM,
        )
        self.control_status.pack(pady=(8, 0))

    def _build_footer(self) -> None:
        footer = ctk.CTkLabel(self, text=f"v{APP_VERSION}", text_color="#9a9aa38c", font=T.FONT_XS)
        footer.pack(pady=(8, 16))

    def _show_onboarding(self) -> None:
        self.control_frame.pack_forget()
        self.onboarding.pack(fill="x", padx=20, pady=8)
        self.onboarding.reset()

    def _show_control(self, name: str) -> None:
        self.onboarding.pack_forget()
        self.device_name.configure(text=name)
        self.control_frame.pack(fill="both", expand=True, padx=20, pady=8)
        self._set_control_status("")

    def _connect(self) -> None:
        self.onboarding.set_status("Connecting…")
        self.onboarding.set_connect_enabled(False)

        self.worker.submit(
            self.device.connect(),
            on_success=self._connect_done,
            on_error=self._connect_error,
        )

    def _connect_done(self, result: dict) -> None:
        self.after(0, lambda: self._handle_connect_result(result))

    def _connect_error(self, exc: BaseException) -> None:
        self.after(0, lambda: self._handle_connect_result({"ok": False, "message": str(exc)}))

    def _handle_connect_result(self, result: dict) -> None:
        self.onboarding.set_connect_enabled(True)
        if result.get("ok"):
            self._show_control(result.get("name") or self.device.device_name)
        else:
            self.onboarding.set_status(result.get("message", "Connect failed"))

    def _disconnect(self) -> None:
        self.dock.close()
        self.mask.clear_active()

        def done(_result: dict) -> None:
            self.after(0, self._show_onboarding)

        self.worker.submit(self.device.disconnect(), on_success=done)

    def _open_zone(self, zone: str) -> None:
        self.mask.set_active(zone)
        self.dock.open_zone(zone)

    def _dock_closed(self) -> None:
        self.mask.clear_active()

    def _set_control_status(self, message: str) -> None:
        self.control_status.configure(text=message or "")

    def _on_close(self) -> None:
        if self.device.is_connected:
            self.worker.submit(self.device.disconnect())
        self.worker.shutdown()
        self.destroy()


def main() -> None:
    app = HazelRevivalApp()
    app.mainloop()


if __name__ == "__main__":
    main()
