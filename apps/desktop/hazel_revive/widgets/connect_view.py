"""Connect screen — matches apps/mobile connect flow."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from hazel_revive.log import get_logger
from zephyr_re.ble.scanner import BleDevice

log = get_logger()


class ConnectView(QWidget):
    connect_requested = pyqtSignal(object)
    scan_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._devices: list[BleDevice] = []
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Connect Zephyr")
        title.setObjectName("heading")
        layout.addWidget(title)

        hint = QLabel(
            "Scan for your mask, select it, then connect. "
            "If the list is empty, pair Razer Zephyr in system Bluetooth first."
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        row = QHBoxLayout()
        row.setSpacing(8)
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self._on_scan_clicked)
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setObjectName("btnPrimary")
        self.connect_btn.clicked.connect(self._on_connect)
        self.connect_btn.setEnabled(False)
        row.addWidget(self.scan_btn)
        row.addWidget(self.connect_btn)
        layout.addLayout(row)

        self.list = QListWidget()
        self.list.setMinimumHeight(160)
        self.list.currentRowChanged.connect(self._on_selection)
        layout.addWidget(self.list)
        layout.addStretch()

    def _on_scan_clicked(self) -> None:
        log.info("Scan button clicked")
        self.scan_requested.emit()

    def set_devices(self, devices: list[BleDevice]) -> None:
        self._devices = devices
        self.list.blockSignals(True)
        self.list.clear()
        for dev in devices:
            name = dev.name or "Unknown device"
            live = "advertising" if dev.is_live() else "paired/offline"
            self.list.addItem(QListWidgetItem(f"{name}  —  {live}"))
        self.list.blockSignals(False)

        if devices:
            self.list.setCurrentRow(0)
            self.connect_btn.setEnabled(True)
            log.info("Device list updated: %d item(s), first selected", len(devices))
        else:
            self.connect_btn.setEnabled(False)
            log.warning("Device list empty after scan")

    def set_busy(self, busy: bool) -> None:
        self.scan_btn.setEnabled(not busy)
        has_selection = self.list.currentRow() >= 0 and bool(self._devices)
        self.connect_btn.setEnabled(not busy and has_selection)

    def _on_selection(self, row: int) -> None:
        enabled = row >= 0 and row < len(self._devices)
        self.connect_btn.setEnabled(enabled)
        if enabled:
            dev = self._devices[row]
            log.debug("Selected device row=%d name=%s address=%s", row, dev.name, dev.address)

    def _on_connect(self) -> None:
        row = self.list.currentRow()
        log.info("Connect button clicked (row=%d, devices=%d)", row, len(self._devices))
        if row < 0 or row >= len(self._devices):
            log.warning("Connect clicked with no valid selection")
            return
        device = self._devices[row]
        log.info("Emitting connect_requested for %s (%s)", device.name, device.address)
        self.connect_btn.setEnabled(False)
        self.connect_requested.emit(device)
