# Web app

Browser UI for the Razer Zephyr using **Web Bluetooth**. Limited platform support — works best on **Chromium/Chrome** (desktop Linux, Windows, Android). macOS and iOS are not supported for BLE connection.

## Run locally

Pair the mask in system Bluetooth settings first, then:

```bash
./run.sh
```

Open **https://127.0.0.1:8765** in Chromium or Chrome and accept the self-signed certificate once.

**Linux + Chromium:** enable `chrome://flags/#enable-experimental-web-platform-features`, relaunch, reload.

Do **not** open `public/index.html` as a file — Web Bluetooth requires the HTTPS server above.

**LAN:** the server listens on all interfaces (`https://192.168.x.x:8765`) for phone/tablet on the same network (Android Chrome only).

## Troubleshooting

1. **Browser:** Chromium or Edge — not Firefox.
2. **URL:** `https://127.0.0.1:8765` via `./run.sh` — not `file://`, not plain `http://`.
3. The page **Diagnostics** panel should show `Secure context: true` and `navigator.bluetooth: yes`.

## Layout

```
public/
  index.html      # UI shell
  css/app.css
  js/             # Web Bluetooth transport, protocol, UI
  assets/         # Mask photo
serve.py          # HTTPS static file server
run.sh            # Start server + open browser
```

Imported from [Hazel-Revival-Project](https://github.com/AlanMet/Hazel-Revival-Project).
