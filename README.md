# Razer Zephyr

Open-source BLE control for the Razer Zephyr. The official Hazel app was discontinued; this library implements the same fan and lighting features.

## Layout

```
docs/features.md     User-facing feature list
src/zephyr_re/       Product library + zephyr-re CLI
src/zephyr_re_dev/   RE tools (optional): zephyr-re-dev
research/            Protocol notes and findings
tools/               Emulator, Frida, probe configs
legacy/apk/          Original Hazel APK (not in git)
```

## Install

Python 3.11+ recommended on macOS:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -e .
```

## Use

```bash
zephyr-re
```

Pair the mask first (hold multifunction ~4s until internal LEDs blink blue).

### Library

```python
import asyncio
from zephyr_re import Zephyr

async def main():
    z = Zephyr()
    await z.connect()
    await z.fan_low()
    await z.external_wave()
    await z.disconnect()

asyncio.run(main())
```

### Architecture

| Layer | Module |
|-------|--------|
| Transport | `zephyr_re.ble.connector.ZephyrConnector` |
| Features | `zephyr_re.Zephyr` — one method per app feature |
| Packets | `zephyr_re.protocol.packets` |
| Vendor I/O | `zephyr_re.protocol.vendor` |

## Dev / reverse engineering

```bash
pip install -e .
zephyr-re-dev
```

See [research/README.md](research/README.md). Emulator setup: [research/hazel-app-ui.md](research/hazel-app-ui.md).
