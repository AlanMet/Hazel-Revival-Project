# Web app

Browser UI for the Razer Zephyr using **Web Bluetooth**. Works best on **Chromium/Chrome** (desktop Linux, Windows, macOS, Android). iOS Safari is not supported — use Bluefy on iPhone.

## Run locally

Pair the mask in system Bluetooth settings first, then:

```bash
./run.sh
```

Open **http://127.0.0.1:8765** in Chromium or Chrome.

**Linux + Chromium:** enable `chrome://flags/#enable-experimental-web-platform-features`, relaunch, reload.

Do **not** open `public/index.html` as a file — Web Bluetooth requires the local server above.

**macOS:** disconnect the mask in System Settings → Bluetooth before connecting in Chrome. If Web Bluetooth fails, use `./apps/desktop/run.sh` instead.

## Troubleshooting

1. **Browser:** Chromium or Edge — not Firefox.
2. **URL:** `http://127.0.0.1:8765` via `./run.sh` — not `file://`, not a LAN IP.
3. The page **Diagnostics** panel should show `Secure context: true` and `navigator.bluetooth: yes`.

## Layout

```
public/
  index.html      # UI shell
  css/app.css
  js/             # Web Bluetooth transport, protocol, UI
  assets/         # Mask photo
serve.py          # HTTP static file server
run.sh            # Start server + open browser
```

Imported from [Hazel-Revival-Project](https://github.com/AlanMet/Hazel-Revival-Project).
