"""User-local settings (known devices)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

from zephyr_re.constants import DEVICE_NAME_PATTERNS

_GATT_MAP = Path(__file__).resolve().parents[2] / "docs" / "config" / "gatt_map.yaml"


def as_str(value: object | None) -> str | None:
    if value is None:
        return None
    return str(value)


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    root = Path(base) if base else Path.home() / ".config"
    return root / "hazel-revive"


def known_devices_path() -> Path:
    return config_dir() / "known_devices.yaml"


def load_known_devices() -> list[tuple[str, str | None]]:
    path = known_devices_path()
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    out: list[tuple[str, str | None]] = []
    for entry in raw.get("devices") or []:
        if isinstance(entry, dict) and entry.get("address"):
            out.append((str(entry["address"]), as_str(entry.get("name"))))
    return out


def save_known_device(address: str, name: str | None = None) -> None:
    path = known_devices_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    by_address = {addr: nm for addr, nm in load_known_devices()}
    existing = by_address.get(address)
    by_address[address] = as_str(name) or existing
    ordered = sorted(
        by_address.items(),
        key=lambda item: (0 if item[1] and "zephyr" in item[1].lower() else 1, item[1] or ""),
    )
    payload = {"devices": [{"name": nm, "address": addr} for addr, nm in ordered[:20]]}
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def device_name_patterns() -> list[str]:
    if _GATT_MAP.exists():
        raw = yaml.safe_load(_GATT_MAP.read_text(encoding="utf-8")) or {}
        patterns = raw.get("device_name_patterns")
        if isinstance(patterns, list) and patterns:
            return [str(p) for p in patterns]
    return list(DEVICE_NAME_PATTERNS)
