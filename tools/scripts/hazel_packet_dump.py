#!/usr/bin/env python3
"""Print Hazel BLE write frames (dev packet builders).

Usage:
  python tools/scripts/hazel_packet_dump.py
  python tools/scripts/hazel_packet_dump.py --fan high
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from zephyr_re.constants import EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE
from zephyr_re.protocol.base import FanSpeed
from zephyr_re_dev.protocol.hazel_write import (
    HazelWritePair,
    brightness_packets,
    effect_off_v3_packets,
    effect_packets,
    fan_speed_packets,
    reference_write_pairs,
    static_color_packets,
)

FAN_LEVEL = {"off": FanSpeed.OFF, "low": FanSpeed.LOW, "high": FanSpeed.HIGH}
COLORS = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
}


def _print_pair(label: str, header: bytes, payload: bytes) -> None:
    from zephyr_re.util.hexio import format_hex

    print(f"\n# {label}")
    print(f"header:  {format_hex(header)}")
    print(f"payload: {format_hex(payload)}")


def _print_writes(pair: HazelWritePair) -> None:
    _print_pair(pair.name, pair.header, pair.payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Dump Hazel vendor write packets")
    parser.add_argument("--all", action="store_true", help="Print reference write sequence")
    parser.add_argument("--fan", choices=list(FAN_LEVEL.keys()))
    parser.add_argument("--static", choices=list(COLORS.keys()))
    parser.add_argument("--zone", choices=["external", "internal"], default="external")
    parser.add_argument("--req", type=lambda x: int(x, 0), default=0x30)
    args = parser.parse_args()

    if args.all:
        for pair in reference_write_pairs(args.req):
            _print_writes(pair)
        return

    req = args.req
    if args.fan:
        h, p = fan_speed_packets(req, FAN_LEVEL[args.fan])
        _print_pair(f"fan {args.fan}", h, p)
        return

    if args.static:
        zone = EXTERNAL_LIGHT_ZONE if args.zone == "external" else INTERNAL_LIGHT_ZONE
        r, g, b = COLORS[args.static]
        h, p = static_color_packets(req, r, g, b, zone)
        _print_pair(f"static {args.static} zone 0x{zone:02X}", h, p)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
