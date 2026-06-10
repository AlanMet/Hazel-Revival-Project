# Firmware update — Razer Zephyr (Hazel APK)

The Hazel app supports OTA firmware updates. This is **separate from** the normal vendor lighting/fan protocol (`52401524`).

## What the app does

| Step | Source | Behavior |
|------|--------|----------|
| Bundled FW | `assets/hazel/01.00.09.00.zip` | Shipped with APK; version read via `00 81 00 00` |
| Update check | `FirmwareUpdateHazelAdapter.checkForFirmwareUpdateFromWeb` | HTTP JSON from Razer server (`firmware_version`, `url`, `min_android_build_version`) |
| Compare | Local `getLoadedVersion()` vs server | Prompts user if server version is newer |
| Enter bootloader | `Hazel.createBootGoToLoaderMode()` | Two writes: `{req} 01 00 00 01 02 00 00` + `01` |
| Flash | `no.nordicsemi.android.dfu` (Nordic DFU) | `AudioApplication.startFirmwareUpdate(context, macPlusOne(), zipPath)` |
| Reconnect | After DFU completes | App retries reconnect up to 5× |

**Not** a simple “hey update available” notify on the normal GATT channel — it’s a full **Nordic Semiconductor DFU** session to a bootloader address (`macPlusOne()`).

## Implications for this tool

- **Read firmware version** — already works (`00 81 00 00` → `01.00.09.00`).
- **Detect “update available”** — would need the same HTTP endpoint the APK uses (or manual version compare).
- **Apply update** — requires implementing or invoking Nordic DFU after bootloader entry; **do not probe bootloader in casual sessions** (disconnects from normal protocol).

## Bootloader packet (document only — dangerous to run)

```text
write[1]  {req} 01 00 00 01 02 00 00
write[2]  01
```

## Factory reset (related, also dangerous)

```text
{req} 00 00 00 01 01 00 00
```

Single-packet `Hazel.createFactoryReset()` — not implemented in tool.
