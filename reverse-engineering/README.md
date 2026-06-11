# Reverse engineering

For programmers working on the BLE protocol, probes, or the old Hazel APK — not needed to use the mask.

## Repo layout

```
reverse-engineering/
├── zephyr_re/           BLE library + zephyr-re CLI
├── src/zephyr_re_dev/   probe tooling + zephyr-re-dev CLI
├── research/            protocol notes and findings
├── tools/               GATT configs, Frida, emulator scripts
└── legacy/              Hazel APK (not in git)
```

## Setup

From the repo root (same install as end users):

```bash
pip install -e .
```

## Tools

| Command | Purpose |
|---------|---------|
| `zephyr-re` | Control the mask (same as users run) |
| `zephyr-re-dev` | Interactive probes, GATT dumps, packet experiments |

Python library:

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

API entry point: [`zephyr_re/zephyr.py`](zephyr_re/zephyr.py).

## Docs

| Doc | Contents |
|-----|----------|
| [research/README.md](research/README.md) | Index of all research notes |
| [research/protocol.md](research/protocol.md) | Command bytes and correlation |
| [research/hazel-app-ui.md](research/hazel-app-ui.md) | Hazel APK in an emulator + Frida mock |
| [tools/config/gatt_map.yaml](tools/config/gatt_map.yaml) | Verified GATT commands |
| [tools/config/probe_candidates.yaml](tools/config/probe_candidates.yaml) | Experimental write variants |

Emulator (no hardware):

```bash
./reverse-engineering/tools/scripts/setup-android-emulator.sh
./reverse-engineering/tools/scripts/run-hazel-mock-emulator.sh
```

Future user-facing UI will live in [`source/`](../source/) at the repo root.
