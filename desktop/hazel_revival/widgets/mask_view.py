"""Interactive mask photo with zone hotspots."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageTk

from hazel_revival import theme as T

ZONES = {
    "external": {"x": 0.175, "y": 0.54, "ring": 0.14},
    "internal": {"x": 0.345, "y": 0.575, "ring": 0.10},
    "fan": {"x": 0.525, "y": 0.63, "ring": 0.12},
}


class MaskView(ctk.CTkFrame):
    def __init__(self, master, *, on_zone, **kwargs) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self._on_zone = on_zone
        self._active: str | None = None
        self._zone_items: dict[str, int] = {}
        self._label_items: dict[str, int] = {}
        self._photo: ImageTk.PhotoImage | None = None
        self._img_size = (560, 375)

        self.canvas = tk.Canvas(
            self,
            width=self._img_size[0],
            height=self._img_size[1],
            bg=T.BG,
            highlightthickness=0,
            bd=0,
        )
        self.canvas.pack()

        if T.MASK_IMAGE.is_file():
            img = Image.open(T.MASK_IMAGE).convert("RGBA")
            img = img.resize(self._img_size, Image.Resampling.LANCZOS)
            self._photo = ImageTk.PhotoImage(img)
            self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
        else:
            self.canvas.create_rectangle(
                0,
                0,
                *self._img_size,
                fill="#1a1a1e",
                outline=T.BORDER,
            )
            self.canvas.create_text(
                self._img_size[0] // 2,
                self._img_size[1] // 2,
                text="mask.jpg missing",
                fill=T.MUTED,
            )

        for zone_id, cfg in ZONES.items():
            self._draw_zone(zone_id, cfg)

    def _draw_zone(self, zone_id: str, cfg: dict) -> None:
        w, h = self._img_size
        cx, cy = cfg["x"] * w, cfg["y"] * h
        r = cfg["ring"] * w / 2

        ring = self.canvas.create_oval(
            cx - r,
            cy - r,
            cx + r,
            cy + r,
            outline="#44d62c73",
            width=2,
            fill="#44d62c18",
            tags=(zone_id, "ring"),
        )
        label = self.canvas.create_text(
            cx,
            cy + r + 14,
            text=zone_id.capitalize(),
            fill=T.TEXT,
            font=("Inter", 9, "bold"),
            tags=(zone_id, "label"),
        )
        self._zone_items[zone_id] = ring
        self._label_items[zone_id] = label

        for item in (ring, label):
            self.canvas.tag_bind(item, "<Enter>", lambda _e, z=zone_id: self._hover(z, True))
            self.canvas.tag_bind(item, "<Leave>", lambda _e, z=zone_id: self._hover(z, False))
            self.canvas.tag_bind(item, "<Button-1>", lambda _e, z=zone_id: self._click(z))

    def _hover(self, zone_id: str, inside: bool) -> None:
        if self._active == zone_id:
            return
        color = "#44d62ccc" if inside else "#44d62c73"
        self.canvas.itemconfigure(self._zone_items[zone_id], outline=color)

    def _click(self, zone_id: str) -> None:
        if self._active == zone_id:
            self.clear_active()
            return
        self.set_active(zone_id)
        self._on_zone(zone_id)

    def set_active(self, zone_id: str | None) -> None:
        self._active = zone_id
        for zid, item in self._zone_items.items():
            active = zid == zone_id
            self.canvas.itemconfigure(
                item,
                outline=T.ACCENT if active else "#44d62c73",
                width=3 if active else 2,
                fill="#44d62c55" if active else "#44d62c18",
            )
            self.canvas.itemconfigure(
                self._label_items[zid],
                fill="#0a0a0a" if active else T.TEXT,
            )

    def clear_active(self) -> None:
        self._active = None
        for zid in self._zone_items:
            self.canvas.itemconfigure(
                self._zone_items[zid],
                outline="#44d62c73",
                width=2,
                fill="#44d62c18",
            )
            self.canvas.itemconfigure(self._label_items[zid], fill=T.TEXT)
