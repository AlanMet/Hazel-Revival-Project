# Hazel Revive

Open-source control for the **Razer Zephyr** mask, fan speed and lighting over Bluetooth.

Razer discontinued the official Hazel app. This project replaces it.

## Documentation

**[docs/](docs/README.md)** explains how the mask works and how to control it:

- [Bluetooth basics](docs/bluetooth-basics.md)
- [Protocol cheat sheet](docs/protocol.md)
- [Reading device state](docs/device-state.md)
- [Features](docs/features.md)

**[research/](research/README.md)** holds reverse-engineering notes, session logs, and probe history. Optional reading.

## Apps

| App | Run |
|-----|-----|
| Desktop (Python + PyQt6) | `./apps/desktop/run.sh` |
| Mobile (Capacitor) | `cd apps/mobile && npm run build && npx cap sync` |
| Web (Web Bluetooth) | `./apps/web/run.sh` → http://127.0.0.1:8765 |
| CLI smoke test | `python -m zephyr_re.cli.smoke --scan` |

Install the Python library once: `pip install -e ".[desktop]"` from the repo root.

## Status

Early development. Protocol layer and basic UIs are in place; verify on hardware with a paired Zephyr.

## License

GPL-2.0, see [LICENSE.md](LICENSE.md).
