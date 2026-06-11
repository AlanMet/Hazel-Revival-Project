"""Pair → Connect walkthrough."""

from __future__ import annotations

import customtkinter as ctk

from hazel_revival import theme as T


class OnboardingView(ctk.CTkFrame):
    def __init__(self, master, *, on_continue, on_connect, **kwargs) -> None:
        super().__init__(master, fg_color=T.SURFACE_GLASS, corner_radius=16, **kwargs)
        self._on_continue = on_continue
        self._on_connect = on_connect
        self._step = 1

        self.progress = ctk.CTkFrame(self, fg_color="transparent")
        self.progress.pack(fill="x", padx=20, pady=(20, 0))

        self._dots: list[ctk.CTkLabel] = []
        for i, label in enumerate(("Pair", "Connect"), start=1):
            row = ctk.CTkFrame(self.progress, fg_color="transparent")
            row.pack(side="left", expand=True, fill="x")
            dot = ctk.CTkLabel(row, text="●", text_color=T.MUTED, font=("Inter", 14))
            dot.pack()
            ctk.CTkLabel(row, text=label, text_color=T.MUTED, font=T.FONT_XS).pack()
            self._dots.append(dot)

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=20, pady=16)

        self.phase_pair = ctk.CTkFrame(self.body, fg_color="transparent")
        self.phase_connect = ctk.CTkFrame(self.body, fg_color="transparent")

        self._build_pair_phase()
        self._build_connect_phase()

        self.status = ctk.CTkLabel(
            self,
            text="",
            text_color=T.MUTED,
            font=T.FONT_SM,
            wraplength=T.MAX_WIDTH - 80,
        )
        self.status.pack(padx=20, pady=(0, 20))

        self.phase_pair.pack(fill="both", expand=True)
        self._set_step(1)

    def _build_pair_phase(self) -> None:
        ctk.CTkLabel(
            self.phase_pair,
            text="Pair your mask",
            font=T.DISPLAY_SM,
            text_color=T.TEXT,
        ).pack(pady=(8, 4))
        ctk.CTkLabel(
            self.phase_pair,
            text="Use your system Bluetooth settings — not this app.",
            text_color=T.MUTED,
            font=T.FONT_SM,
            wraplength=360,
        ).pack(pady=(0, 12))

        steps = (
            "Hold the multifunction button for about 4 seconds",
            "Wait until the internal LEDs blink blue twice",
            "Add Razer Zephyr in Bluetooth settings",
        )
        for i, step in enumerate(steps, 1):
            ctk.CTkLabel(
                self.phase_pair,
                text=f"{i}. {step}",
                anchor="w",
                justify="left",
                text_color=T.TEXT,
                font=T.FONT,
                wraplength=380,
            ).pack(fill="x", pady=3)

        ctk.CTkButton(
            self.phase_pair,
            text="Continue →",
            command=self._continue,
            fg_color=T.ACCENT,
            hover_color="#3bc424",
            text_color="#0a0a0a",
            font=("Inter", 14, "bold"),
            height=44,
        ).pack(fill="x", pady=(20, 0))

    def _build_connect_phase(self) -> None:
        ctk.CTkLabel(
            self.phase_connect,
            text="Connect to mask",
            font=T.DISPLAY_SM,
            text_color=T.TEXT,
        ).pack(pady=(8, 4))
        ctk.CTkLabel(
            self.phase_connect,
            text="This app links to your already-paired mask over Bluetooth.",
            text_color=T.MUTED,
            font=T.FONT_SM,
            wraplength=360,
        ).pack(pady=(0, 16))

        self.connect_btn = ctk.CTkButton(
            self.phase_connect,
            text="Connect mask →",
            command=self._on_connect,
            fg_color=T.ACCENT,
            hover_color="#3bc424",
            text_color="#0a0a0a",
            font=("Inter", 14, "bold"),
            height=44,
        )
        self.connect_btn.pack(fill="x")

        ctk.CTkLabel(
            self.phase_connect,
            text="Make sure Razer Zephyr appears in your system Bluetooth list first.",
            text_color=T.MUTED,
            font=T.FONT_XS,
            wraplength=380,
        ).pack(pady=(12, 0))

    def _set_step(self, step: int) -> None:
        self._step = step
        for i, dot in enumerate(self._dots, start=1):
            if i < step:
                dot.configure(text_color=T.ACCENT)
            elif i == step:
                dot.configure(text_color=T.ACCENT)
            else:
                dot.configure(text_color=T.MUTED)

    def _continue(self) -> None:
        self._set_step(2)
        self.phase_pair.pack_forget()
        self.phase_connect.pack(fill="both", expand=True)
        self.status.configure(text="")
        self._on_continue()

    def set_status(self, message: str) -> None:
        self.status.configure(text=message or "")

    def set_connect_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        self.connect_btn.configure(state=state)

    def reset(self) -> None:
        self.phase_connect.pack_forget()
        self.phase_pair.pack(fill="both", expand=True)
        self._set_step(1)
        self.set_status("")
        self.set_connect_enabled(True)
