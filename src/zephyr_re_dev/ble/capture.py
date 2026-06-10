"""Session log for all GATT traffic during reverse engineering."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from zephyr_re_dev.config import project_root
from zephyr_re_dev.util.frame_decode import decode_gatt_payload, decode_vendor_frame
from zephyr_re.util.hexio import format_hex


def _short_ts(iso: str) -> str:
    """Compact timestamp for line-oriented logs (UTC)."""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%H:%M:%S.") + f"{dt.microsecond // 1000:03d}"
    except ValueError:
        return iso


def _short_char(uuid: str | None) -> str:
    if not uuid:
        return ""
    u = uuid.lower()
    if u.startswith("0000") and len(u) >= 8:
        return u[:8]
    parts = u.split("-", 1)
    return parts[0][:8] if parts else u[:8]


@dataclass
class CaptureEntry:
    timestamp: str
    direction: str  # write | read | notify | connect | disconnect | info | operation | poll
    characteristic: str | None
    data_hex: str | None
    message: str | None = None


@dataclass
class GattCaptureLog:
    """In-memory capture log with live append to a session .log file."""

    session_id: str = field(default_factory=lambda: datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S"))
    entries: list[CaptureEntry] = field(default_factory=list)
    live_path: Path | None = None
    _live_ready: bool = field(default=False, repr=False)

    def __post_init__(self) -> None:
        if self.live_path is None:
            self.live_path = project_root() / "research" / "captures" / f"session-{self.session_id}.log"

    def _ensure_live(self) -> Path:
        path = self.live_path
        assert path is not None
        path.parent.mkdir(parents=True, exist_ok=True)
        if not self._live_ready:
            if not path.exists():
                started = datetime.now(timezone.utc).isoformat()
                path.write_text(
                    f"# Zephyr RE session {self.session_id}\n"
                    f"# started {started}\n"
                    f"# tail -f {path}\n"
                    f"# Lines: TIME DIR CHAR HEX | decode hint\n\n",
                    encoding="utf-8",
                )
            self._live_ready = True
        return path

    def _append_live(self, line: str) -> None:
        path = self._ensure_live()
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            if not line.endswith("\n"):
                handle.write("\n")
            handle.flush()

    def format_line(self, entry: CaptureEntry) -> str:
        ts = _short_ts(entry.timestamp)
        direction = entry.direction.upper().ljust(9)
        char = _short_char(entry.characteristic)
        parts = [ts, direction]
        if char:
            parts.append(char)
        if entry.data_hex:
            parts.append(entry.data_hex)
        if entry.message:
            parts.append(f"| {entry.message}")
        return "  ".join(parts)

    def log(
        self,
        direction: str,
        *,
        characteristic: str | None = None,
        data: bytes | None = None,
        message: str | None = None,
    ) -> None:
        entry = CaptureEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            direction=direction,
            characteristic=characteristic,
            data_hex=format_hex(data) if data is not None else None,
            message=message,
        )
        self.entries.append(entry)
        self._append_live(self.format_line(entry))

    def log_section(self, title: str) -> None:
        """Visual break in the live log before a user operation or probe."""
        self._append_live(f"\n# --- {title} ---")
        self.log("info", message=f"--- {title} ---")

    def log_operation(
        self,
        name: str,
        *,
        index: int | None = None,
        total: int | None = None,
        result: str,
        writes: list[bytes] | None = None,
        frames: list[bytes] | None = None,
        detail: str | None = None,
    ) -> None:
        """Summarize an attempted operation with decoded replies."""
        label = name
        if index is not None and total is not None:
            label = f"[{index}/{total}] {name}"
        reply_count = len(frames) if frames else 0
        msg = f"{label} → {result} ({reply_count} replies)"
        if detail:
            msg += f" | {detail}"
        self.log("operation", message=msg)
        if writes:
            for i, packet in enumerate(writes, 1):
                hint = decode_gatt_payload("52401524-F97C-7F90-0E7F-6C6F4E36DB1C", packet)
                line = f"    sent[{i}] {format_hex(packet)}"
                if hint:
                    line += f" | {hint}"
                self._append_live(line)
        if frames:
            for i, frame in enumerate(frames, 1):
                self._append_live(f"    reply[{i}] {format_hex(frame)} | {decode_vendor_frame(frame)}")
        elif writes:
            self._append_live("    reply: (none within timeout)")

    def log_command_result(self, label: str, message: str, frames: list[bytes] | None = None) -> None:
        """Log outcome of a high-level control command."""
        detail = message
        if frames:
            detail += f" | {len(frames)} frame(s)"
        self.log("operation", message=f"{label} → {detail}")
        if frames:
            for i, frame in enumerate(frames, 1):
                self._append_live(f"    reply[{i}] {format_hex(frame)} | {decode_vendor_frame(frame)}")

    def log_listen_summary(self, captures: list) -> None:
        """Summarize a notification listen window (NotifyCapture list)."""
        if not captures:
            self.log("info", message="listen: no notifications in window")
            return
        total = sum(len(c.frames) for c in captures)
        self.log("info", message=f"listen: {total} frame(s) on {len(captures)} characteristic(s)")
        for cap in captures:
            char = _short_char(cap.char_uuid)
            self._append_live(f"    {char}: {len(cap.frames)} frame(s)")
            for i, frame in enumerate(cap.frames[:10], 1):
                self._append_live(f"      [{i}] {format_hex(frame)} | {decode_gatt_payload(cap.char_uuid, frame)}")
            if len(cap.frames) > 10:
                self._append_live(f"      … +{len(cap.frames) - 10} more")

    def log_device_state(self, state: object) -> None:
        """Append decoded device state summary to the live log."""
        self._append_live("\n# --- device state ---")
        self.log("info", message=f"--- device state @ {state.synced_at} ---")
        pct = getattr(state, "external_brightness_percent", None)
        raw_b = getattr(state, "external_brightness", None)
        if pct is not None:
            bright = f"    ext brightness: {pct}% (zone 0x05)"
            if raw_b is not None and raw_b > 100:
                bright += f", raw 0x{raw_b:02X}"
        elif raw_b is not None:
            bright = f"    ext brightness: {raw_b} (zone 0x05)"
        else:
            bright = "    ext brightness: —"
        int_pct = getattr(state, "internal_brightness_percent", None)
        int_raw = getattr(state, "internal_brightness", None)
        if int_pct is not None:
            int_bright = f"    int brightness: {int_pct}% (zone 0x01)"
        elif int_raw is not None:
            int_bright = f"    int brightness: {int_raw} (zone 0x01)"
        else:
            int_bright = "    int brightness: —"
        fan_src = getattr(state, "fan_speed_source", "assumed")
        fan_val = getattr(state, "fan_speed", None)
        fan_line = f"    fans: {fan_val.value if fan_val is not None else 'off'} ({fan_src})"
        fw = getattr(state, "firmware_version", None)
        charging = getattr(state, "is_charging", None)
        charge_s = "yes" if charging else "no" if charging is not None else "—"
        lines = [
            f"    battery: {state.battery_percent}%"
            if state.battery_percent is not None
            else "    battery: —",
            bright,
            int_bright,
        ]
        if state.external_color is not None:
            c = state.external_color
            lines.append(f"    external color: #{c.r:02X}{c.g:02X}{c.b:02X}")
        elif state.external_color_note:
            lines.append(f"    external color: — ({state.external_color_note})")
        else:
            lines.append("    external color: —")
        lines.append(
            f"    external effect: {state.external_effect}"
            if state.external_effect
            else "    external effect: —"
        )
        internal_effect = getattr(state, "internal_effect", None)
        lines.append(
            f"    internal effect: {internal_effect}" if internal_effect else "    internal effect: —"
        )
        lines.append(fan_line)
        lines.append(f"    internal light: {state.internal_light}")
        lines.append(f"    firmware: {fw}" if fw else "    firmware: —")
        lines.append(f"    charging: {charge_s}")
        for line in lines:
            self._append_live(line)

    def log_read_batch(self, results: list) -> None:
        """Summarize a batch of GATT reads (GattReadResult list)."""
        ok = sum(1 for r in results if r.ok)
        fail = len(results) - ok
        self.log("info", message=f"read batch: {ok} OK, {fail} failed")
        for r in results:
            char = _short_char(r.char_uuid)
            if r.error:
                self._append_live(f"    FAIL {char}: {r.error}")
                continue
            assert r.data is not None
            hint = r.hint or decode_gatt_payload(r.char_uuid, r.data)
            line = f"    OK {char}: {format_hex(r.data)}"
            if hint:
                line += f" | {hint}"
            self._append_live(line)

    def recent(self, limit: int = 50) -> list[CaptureEntry]:
        return self.entries[-limit:]

    def live_tail(self, limit: int = 40) -> list[str]:
        """Last N lines from the on-disk session log."""
        path = self.live_path
        if path is None or not path.exists():
            return []
        lines = path.read_text(encoding="utf-8").splitlines()
        return lines[-limit:]

    def export(self, path: Path) -> Path:
        """Export full session as JSON (use .json extension)."""
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".log":
            path = path.with_suffix(".json")
        payload = {
            "session_id": self.session_id,
            "live_log": str(self.live_path) if self.live_path else None,
            "entries": [asdict(e) for e in self.entries],
        }
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def summary_lines(self, limit: int = 30) -> list[str]:
        lines: list[str] = []
        for e in self.recent(limit):
            lines.append(self.format_line(e))
        return lines
