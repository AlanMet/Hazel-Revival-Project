# Razer Zephyr control

Control your **Razer Zephyr** mask from your computer — fan speed and lighting (internal and external).

Razer discontinued the official **Hazel** app. This project replaces it.

## Desktop app (recommended on PC)

Native window — same UI as the web app, uses system Bluetooth (works on Linux, Windows, macOS):

```bash
./run-desktop.sh
```

Pair the mask in Bluetooth settings first. See [desktop/README.md](desktop/README.md).

## Visual web app (browser)

Graphical UI served locally over HTTPS — needs Chromium + Web Bluetooth:

```bash
./run-local.sh
```

Then open **https://127.0.0.1:8765** in **Chromium or Chrome** (accept the certificate warning once). Pair the mask in system Bluetooth settings, then **Connect** in the app.

**Linux + Chromium:** enable `chrome://flags/#enable-experimental-web-platform-features`, relaunch, reload.

Do **not** open `public/index.html` as a file — Web Bluetooth needs the HTTPS server above.

## Hosted copy (optional)

Same visual app, deployed to GitHub Pages: [alanmet.github.io/Hazel-Revival-Project](https://alanmet.github.io/Hazel-Revival-Project/) — local `./run-local.sh` is usually fresher.

**LAN:** `./run-local.sh` also listens on your Wi‑Fi IP (`https://192.168.x.x:8765`) for phone/tablet on the same network (Android Chrome only; iOS has no Web Bluetooth).

### Troubleshooting “Web Bluetooth not available”

1. **Browser:** Chromium or Edge only — not Firefox.
2. **URL:** `https://127.0.0.1:8765` via `./run-local.sh` — not `file://`, not plain `http://`.
3. The page **Diagnostics** panel should show `Secure context: true` and `navigator.bluetooth: yes`.
4. **Linux:** enable `chrome://flags/#enable-experimental-web-platform-features`, relaunch Chromium.

On Arch: `sudo pacman -S chromium`

## What you need

- Razer Zephyr, paired over Bluetooth to the **same device** running the browser
- **Chrome or Edge** (desktop Linux/macOS/Windows, or Chrome on Android)
- Not Firefox — Mozilla does not ship Web Bluetooth

## Legacy CLI (optional, terminal only)

For RE/debugging — not the visual app:

```bash
./run-cli.sh
```

## What you can control

Fan off / low / high, internal lighting (static, spectrum, breathing, off), external lighting (same plus wave). Full list: [features.md](features.md).

---

**Developers / reverse engineering:** see [reverse-engineering/README.md](reverse-engineering/README.md).
