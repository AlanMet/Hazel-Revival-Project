"""Load dev configuration from tools/config/gatt_map.yaml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


def as_str(value: object | None) -> str | None:
    """Coerce PyObjC NSString and other bridge types to plain str for YAML/JSON."""
    if value is None:
        return None
    return str(value)


def project_root() -> Path:
    """Resolve repository root (directory containing tools/config/)."""
    here = Path(__file__).resolve().parent
    candidate = here.parent.parent
    if (candidate / "tools" / "config" / "gatt_map.yaml").exists():
        return candidate
    cwd = Path.cwd()
    if (cwd / "tools" / "config" / "gatt_map.yaml").exists():
        return cwd
    return candidate


def gatt_map_path() -> Path:
    return project_root() / "tools" / "config" / "gatt_map.yaml"


def known_devices_path() -> Path:
    from zephyr_re.settings import known_devices_path as product_path

    return product_path()


@dataclass
class KnownDevice:
    address: str
    name: str | None = None


@dataclass
class CommandSpec:
    name: str
    write: str | None
    writes: list[str] | None = None
    expect_notify: bool = True
    response_timeout_ms: int = 500

    def write_templates(self) -> list[str]:
        if self.writes:
            return list(self.writes)
        if self.write:
            return [self.write]
        return []


@dataclass
class GattMapConfig:
    device_name_patterns: list[str] = field(default_factory=lambda: ["Zephyr", "Razer", "Hazel"])
    service_uuid: str | None = None
    write_char_uuid: str | None = None
    notify_char_uuid: str | None = None
    extra_notify_char_uuid: str | None = None
    battery_service_char_uuid: str | None = None
    request_id_start: int = 0x30
    commands: dict[str, CommandSpec] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path | None = None) -> GattMapConfig:
        path = path or gatt_map_path()
        if not path.exists():
            return cls()
        raw: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        commands: dict[str, CommandSpec] = {}
        for name, spec in (raw.get("commands") or {}).items():
            if not isinstance(spec, dict):
                continue
            raw_writes = spec.get("writes")
            writes = list(raw_writes) if isinstance(raw_writes, list) else None
            commands[name] = CommandSpec(
                name=name,
                write=spec.get("write"),
                writes=writes,
                expect_notify=bool(spec.get("expect_notify", True)),
                response_timeout_ms=int(spec.get("response_timeout_ms", 500)),
            )
        return cls(
            device_name_patterns=list(raw.get("device_name_patterns") or ["Zephyr", "Razer", "Hazel"]),
            service_uuid=raw.get("service_uuid"),
            write_char_uuid=raw.get("write_char_uuid"),
            notify_char_uuid=raw.get("notify_char_uuid"),
            extra_notify_char_uuid=raw.get("extra_notify_char_uuid"),
            battery_service_char_uuid=raw.get("battery_service_char_uuid"),
            request_id_start=int(raw.get("request_id_start", 0x30)),
            commands=commands,
        )

    def is_configured(self) -> bool:
        return bool(self.write_char_uuid and self.notify_char_uuid)


def load_known_devices(path: Path | None = None) -> list[KnownDevice]:
    path = path or known_devices_path()
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    devices: list[KnownDevice] = []
    for entry in raw.get("devices") or []:
        if not isinstance(entry, dict) or not entry.get("address"):
            continue
        devices.append(
            KnownDevice(
                address=str(entry["address"]),
                name=as_str(entry.get("name")),
            )
        )
    return devices


def save_known_device(address: str, name: str | None = None, path: Path | None = None) -> None:
    """Persist or update a device address for offline/connected discovery."""
    path = path or known_devices_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    devices = load_known_devices(path)
    by_address = {d.address: d for d in devices}
    existing = by_address.get(address)
    safe_name = as_str(name) or (existing.name if existing else None)
    by_address[address] = KnownDevice(
        address=address,
        name=safe_name,
    )
    # Keep Zephyr-like devices first, cap list size
    ordered = list(by_address.values())
    ordered.sort(key=lambda d: (0 if d.name and "zephyr" in d.name.lower() else 1, d.name or ""))
    payload = {
        "devices": [{"name": d.name, "address": d.address} for d in ordered[:20]],
    }
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
