"""CLI smoke test: connect, optional fan command, disconnect."""

from __future__ import annotations

import argparse
import asyncio
import sys

from zephyr_re.protocol.base import CommandStatus
from zephyr_re.zephyr import Zephyr

FAN_COMMANDS = {
    "fan_off": "fan_off",
    "fan_low": "fan_low",
    "fan_high": "fan_high",
}


async def _run(args: argparse.Namespace) -> int:
    zephyr = Zephyr()
    try:
        if args.scan:
            devices = await zephyr.scan(timeout=args.timeout)
            if not devices:
                print("No devices found")
                return 1
            for dev in devices:
                label = dev.name or "Unknown"
                live = "live" if dev.is_live() else "offline"
                print(f"  {label} ({dev.address}) [{live}]")
            return 0

        print("Connecting…")
        await zephyr.connect()
        print(f"Connected: {zephyr.connector.address}")

        if args.sync:
            state = await zephyr.sync_state()
            print(f"Battery: {state.battery_percent}%")
            print(f"Fan: {state.fan_speed.value} ({state.fan_speed_source})")
            print(f"External: {state.external_effect}")
            print(f"Internal: {state.internal_effect}")
            if state.firmware_version:
                print(f"Firmware: {state.firmware_version}")

        for cmd_name in args.command:
            method = getattr(zephyr, FAN_COMMANDS.get(cmd_name, cmd_name), None)
            if method is None:
                print(f"Unknown command: {cmd_name}", file=sys.stderr)
                return 1
            result = await method()
            status = "OK" if result.status == CommandStatus.OK else result.status.value
            print(f"{cmd_name}: {status} — {result.message}")

        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    finally:
        if zephyr.is_connected:
            await zephyr.disconnect()
            print("Disconnected")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Zephyr BLE smoke test")
    parser.add_argument("--scan", action="store_true", help="Scan and list devices")
    parser.add_argument("--sync", action="store_true", help="Sync device state after connect")
    parser.add_argument("--timeout", type=float, default=8.0, help="Scan timeout seconds")
    parser.add_argument(
        "command",
        nargs="*",
        help="Commands: fan_off, fan_low, fan_high, sync_state, …",
    )
    args = parser.parse_args(argv)
    if args.command == ["sync_state"]:
        args.sync = True
        args.command = []
    raise SystemExit(asyncio.run(_run(args)))


if __name__ == "__main__":
    main()
