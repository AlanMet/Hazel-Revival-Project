# Hazel Revival — Desktop App

Native **Python desktop app** with the same visual flow as the web UI:

- Pair → Connect onboarding
- Mask photo with External / Internal / Fan zones
- Control dock (fan, static colour, spectrum, breathing, wave, off)

Uses **bleak** (system Bluetooth) — works on Linux, Windows, and macOS without Web Bluetooth or a browser.

## Run

From the repo root:

```bash
./run-desktop.sh
```

First run creates `.venv` and installs `zephyr-re[desktop]`.

**Arch Linux:** install Tk if the app fails to start:

```bash
sudo pacman -S tk
```

## vs web app

| | Desktop (`./run-desktop.sh`) | Web (`./run-local.sh`) |
|---|---|---|
| UI | Native window | Browser |
| Bluetooth | bleak (OS stack) | Web Bluetooth |
| macOS | Works | Broken |
| Linux | Works | Needs Chromium flag |

The web app in [`public/`](../public/) is unchanged — this lives alongside it in `desktop/`.

## Structure

```
desktop/
  hazel_revival/
    app.py              Main window
    device.py           BLE via zephyr_re
    widgets/            Onboarding, mask, control dock
```

Assets (mask photo) are loaded from [`public/assets/`](../public/assets/) — no duplication.
