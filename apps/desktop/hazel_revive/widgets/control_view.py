"""Zone control screen — btn-grid like apps/mobile."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QColorDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_ZONE_TITLES = {
    "fan": "Fan speed",
    "internal": "Internal lighting",
    "external": "External lighting",
}


class ControlView(QWidget):
    action_requested = pyqtSignal(str, dict)
    back_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._zone: str | None = None
        self._body = QVBoxLayout(self)
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(12)

    def open_zone(self, zone: str) -> None:
        self._zone = zone
        self._clear()
        back = QPushButton("← Back")
        back.clicked.connect(self.back_requested.emit)
        self._body.addWidget(back)

        title = QLabel(_ZONE_TITLES.get(zone, zone))
        title.setObjectName("subheading")
        self._body.addWidget(title)

        grid_host = QWidget()
        grid = QGridLayout(grid_host)
        grid.setSpacing(8)

        if zone == "fan":
            actions = [("Low", "fan_low"), ("High", "fan_high"), ("Off", "fan_off")]
        elif zone == "internal":
            actions = [
                ("Static color", "internal_static_pick"),
                ("Spectrum", "internal_spectrum"),
                ("Breathing", "internal_breathing"),
                ("Off", "internal_off"),
            ]
        else:
            actions = [
                ("Static color", "external_static_pick"),
                ("Spectrum", "external_spectrum"),
                ("Breathing", "external_breathing"),
                ("Wave LTR", "external_wave_ltr"),
                ("Wave fast", "external_wave_fast"),
                ("Off", "external_off"),
            ]

        cols = 2
        for i, (label, action) in enumerate(actions):
            btn = QPushButton(label)
            btn.clicked.connect(lambda _c=False, a=action: self._emit(a))
            grid.addWidget(btn, i // cols, i % cols)

        self._body.addWidget(grid_host)
        self._body.addStretch()

    def _clear(self) -> None:
        while self._body.count():
            item = self._body.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _emit(self, action: str) -> None:
        if action.endswith("_static_pick"):
            color = QColorDialog.getColor(parent=self)
            if not color.isValid():
                return
            base = action.replace("_pick", "")
            self.action_requested.emit(
                base,
                {"r": color.red(), "g": color.green(), "b": color.blue()},
            )
            return
        if action == "external_wave_ltr":
            self.action_requested.emit(
                "external_wave",
                {"left_to_right": True, "speed": "medium"},
            )
            return
        if action == "external_wave_fast":
            self.action_requested.emit(
                "external_wave",
                {"left_to_right": True, "speed": "fast"},
            )
            return
        self.action_requested.emit(action, {})
