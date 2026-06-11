"""Main PyQt6 window."""

from __future__ import annotations

import asyncio

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qasync import asyncSlot

from hazel_revive.device import DeviceController
from hazel_revive.log import connect_log_panel, get_logger, log_file_path
from hazel_revive.styles import app_stylesheet
from hazel_revive.widgets.connect_view import ConnectView
from hazel_revive.widgets.control_view import ControlView
from hazel_revive.widgets.dashboard import DashboardView

log = get_logger()

_SCREEN_CONNECT = 0
_SCREEN_DASHBOARD = 1
_SCREEN_CONTROL = 2


class HazelReviveApp(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Hazel Revive — Razer Zephyr")
        self.setFixedWidth(480)
        self.resize(480, 720)
        self.setStyleSheet(app_stylesheet())

        self.device = DeviceController()
        self._control_zone: str | None = None

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(20, 20, 20, 0)
        outer.setSpacing(0)

        self.stack = QStackedWidget()
        self.connect_view = ConnectView()
        self.dashboard = DashboardView()
        self.control_view = ControlView()
        self.stack.addWidget(self.connect_view)
        self.stack.addWidget(self.dashboard)
        self.stack.addWidget(self.control_view)
        outer.addWidget(self.stack, stretch=1)

        log_row = QHBoxLayout()
        log_row.setContentsMargins(0, 4, 0, 4)
        self.log_toggle = QPushButton("Show log")
        self.log_toggle.setFlat(True)
        self.log_toggle.clicked.connect(self._toggle_log)
        log_row.addWidget(self.log_toggle)
        log_row.addStretch()
        log_hint = QLabel(f"Log file: {log_file_path()}")
        log_hint.setObjectName("muted")
        log_row.addWidget(log_hint)
        outer.addLayout(log_row)

        self.log_panel = QPlainTextEdit()
        self.log_panel.setObjectName("logPanel")
        self.log_panel.setReadOnly(True)
        self.log_panel.setMaximumBlockCount(500)
        self.log_panel.setVisible(False)
        self.log_panel.setFixedHeight(140)
        outer.addWidget(self.log_panel)

        self.status_bar = QLabel("")
        self.status_bar.setObjectName("statusBar")
        self.status_bar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer.addWidget(self.status_bar)

        connect_log_panel(self._append_log)

        self.connect_view.scan_requested.connect(self._on_scan)
        self.connect_view.connect_requested.connect(self._on_connect)
        self.dashboard.disconnect_requested.connect(self._on_disconnect)
        self.dashboard.refresh_requested.connect(self._on_refresh)
        self.dashboard.zone_open_requested.connect(self._open_zone)
        self.control_view.back_requested.connect(self._back_to_dashboard)
        self.control_view.action_requested.connect(self._on_run_action)

        self._set_status(f"Ready — logs at {log_file_path()}")
        log.info("Hazel Revive desktop started")

    def _append_log(self, line: str) -> None:
        self.log_panel.appendPlainText(line)

    def _toggle_log(self) -> None:
        visible = not self.log_panel.isVisible()
        self.log_panel.setVisible(visible)
        self.log_toggle.setText("Hide log" if visible else "Show log")

    def _set_status(self, message: str) -> None:
        self.status_bar.setText(message)

    def closeEvent(self, event) -> None:
        if self.device.is_connected:
            asyncio.ensure_future(self.device.disconnect())
        super().closeEvent(event)

    @asyncSlot()
    async def _on_scan(self) -> None:
        log.info("Starting BLE scan")
        self._set_status("Scanning…")
        self.connect_view.set_busy(True)
        try:
            devices = await self.device.scan()
            self.connect_view.set_devices(devices)
            if devices:
                self._set_status(f"Found {len(devices)} device(s) — select one and tap Connect")
                log.info("Scan complete: %d device(s)", len(devices))
            else:
                self._set_status("No Zephyr devices found — pair in Bluetooth settings, then scan again")
                log.warning("Scan returned no devices")
        except Exception as exc:
            log.exception("Scan failed")
            self._set_status(f"Scan failed: {exc}")
        finally:
            self.connect_view.set_busy(False)

    @asyncSlot(object)
    async def _on_connect(self, device) -> None:
        name = getattr(device, "name", None) or "device"
        addr = getattr(device, "address", None)
        log.info("Connecting to %s (%s)", name, addr)
        self._set_status("Connecting…")
        self.connect_view.set_busy(True)
        try:
            result = await self.device.connect(device)
            if result.get("ok"):
                log.info("Connected: %s", result.get("name", self.device.device_name))
                self.device.on_fan_changed(lambda _s: asyncio.ensure_future(self._refresh_quiet()))
                self.dashboard.apply_state(result.get("state"))
                self.stack.setCurrentIndex(_SCREEN_DASHBOARD)
                self._set_status(result.get("message", "Connected"))
            else:
                msg = result.get("message", "Connect failed")
                log.error("Connect failed: %s", msg)
                self._set_status(msg)
        except Exception as exc:
            log.exception("Connect raised")
            self._set_status(f"Connect failed: {exc}")
        finally:
            self.connect_view.set_busy(False)

    @asyncSlot()
    async def _on_disconnect(self) -> None:
        log.info("Disconnecting")
        self._set_status("Disconnecting…")
        try:
            await self.device.disconnect()
            self.stack.setCurrentIndex(_SCREEN_CONNECT)
            self._set_status("Disconnected")
            log.info("Disconnected")
        except Exception as exc:
            log.exception("Disconnect failed")
            self._set_status(f"Disconnect failed: {exc}")

    @asyncSlot()
    async def _on_refresh(self) -> None:
        self._set_status("Syncing…")
        try:
            result = await self.device.sync()
            if result.get("ok"):
                self.dashboard.apply_state(result.get("state"))
                self._set_status("Synced")
                log.info("State synced")
            else:
                msg = result.get("message", "Sync failed")
                log.error("Sync failed: %s", msg)
                self._set_status(msg)
        except Exception as exc:
            log.exception("Sync failed")
            self._set_status(f"Sync failed: {exc}")

    async def _refresh_quiet(self) -> None:
        try:
            result = await self.device.sync()
            if result.get("ok"):
                self.dashboard.apply_state(result.get("state"))
        except Exception:
            log.exception("Background sync failed")

    def _open_zone(self, zone: str) -> None:
        self._control_zone = zone
        self.control_view.open_zone(zone)
        self.stack.setCurrentIndex(_SCREEN_CONTROL)
        log.debug("Opened control zone: %s", zone)

    def _back_to_dashboard(self) -> None:
        self._control_zone = None
        self.stack.setCurrentIndex(_SCREEN_DASHBOARD)

    @asyncSlot(str, dict)
    async def _on_run_action(self, action: str, opts: dict) -> None:
        log.info("Action %s opts=%s", action, opts)
        self._set_status(f"Sending {action}…")
        method = getattr(self.device, action, None)
        if method is None:
            log.error("Unknown action: %s", action)
            self._set_status(f"Unknown action: {action}")
            return
        try:
            if action == "external_wave":
                presets = self.device.wave_presets()
                rate = presets.get(opts.get("speed", "medium"), presets["medium"])
                result = await method(
                    left_to_right=opts.get("left_to_right", True),
                    rate=rate,
                )
            elif "static" in action:
                result = await method(opts["r"], opts["g"], opts["b"])
            else:
                result = await method()
            if result.get("ok"):
                sync = await self.device.sync()
                if sync.get("ok"):
                    self.dashboard.apply_state(sync.get("state"))
                self._set_status(result.get("message", "OK"))
                log.info("Action %s OK", action)
                self.stack.setCurrentIndex(_SCREEN_DASHBOARD)
            else:
                msg = result.get("message", "Failed")
                log.error("Action %s failed: %s", action, msg)
                self._set_status(msg)
        except Exception as exc:
            log.exception("Action %s raised", action)
            self._set_status(f"Failed: {exc}")
