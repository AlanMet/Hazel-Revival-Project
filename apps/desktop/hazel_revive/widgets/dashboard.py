"""Dashboard — fan / lighting rows like apps/mobile."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from zephyr_re.device.state import DeviceState
from zephyr_re.protocol.base import FanSpeed


class _DashboardRow(QFrame):
    clicked = pyqtSignal()

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dashboardRow")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        self.title_label = QLabel(title)
        self.detail_label = QLabel("—")
        self.detail_label.setObjectName("muted")
        layout.addWidget(self.title_label)
        layout.addStretch()
        layout.addWidget(self.detail_label)

    def mousePressEvent(self, event) -> None:
        self.clicked.emit()
        super().mousePressEvent(event)

    def set_detail(self, text: str) -> None:
        self.detail_label.setText(text)


class DashboardView(QWidget):
    zone_open_requested = pyqtSignal(str)
    disconnect_requested = pyqtSignal()
    refresh_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Zephyr")
        title.setObjectName("heading")
        layout.addWidget(title)

        self.battery_label = QLabel("Battery: —")
        self.battery_label.setObjectName("accent")
        layout.addWidget(self.battery_label)

        self.firmware_label = QLabel("")
        self.firmware_label.setObjectName("muted")
        layout.addWidget(self.firmware_label)

        self.fan_row = _DashboardRow("Fan speed")
        self.fan_row.clicked.connect(lambda: self.zone_open_requested.emit("fan"))
        layout.addWidget(self.fan_row)

        self.internal_row = _DashboardRow("Internal lighting")
        self.internal_row.clicked.connect(lambda: self.zone_open_requested.emit("internal"))
        layout.addWidget(self.internal_row)

        self.external_row = _DashboardRow("External lighting")
        self.external_row.clicked.connect(lambda: self.zone_open_requested.emit("external"))
        layout.addWidget(self.external_row)

        row = QHBoxLayout()
        row.setSpacing(8)
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_requested.emit)
        disconnect_btn = QPushButton("Disconnect")
        disconnect_btn.clicked.connect(self.disconnect_requested.emit)
        row.addWidget(refresh_btn)
        row.addWidget(disconnect_btn)
        layout.addLayout(row)
        layout.addStretch()

    def apply_state(self, state: DeviceState | None) -> None:
        if state is None:
            return
        bat = f"{state.battery_percent}%" if state.battery_percent is not None else "—"
        charging = " (charging)" if state.is_charging else ""
        self.battery_label.setText(f"Battery: {bat}{charging}")
        if state.firmware_version:
            self.firmware_label.setText(f"Firmware {state.firmware_version}")
        else:
            self.firmware_label.setText("")

        fan_labels = {FanSpeed.OFF: "Off", FanSpeed.LOW: "Low", FanSpeed.HIGH: "High"}
        self.fan_row.set_detail(fan_labels.get(state.fan_speed, state.fan_speed.value))

        internal = state.internal_effect or "—"
        if state.internal_light_on is False:
            internal = "off"
        self.internal_row.set_detail(internal)

        external = state.external_effect or "—"
        if state.external_color_note:
            external = state.external_color_note
        self.external_row.set_detail(external)
