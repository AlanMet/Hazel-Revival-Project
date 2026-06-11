# Research findings: Razer Zephyr

What we tested on real hardware and what failed. For how to control the mask, see [../docs/bluetooth-basics.md](../docs/bluetooth-basics.md).

Sources: Hazel APK (`archive/apk/decompiled/`), Razer mouse notes ([opensnek-BLE_PROTOCOL.md](opensnek-BLE_PROTOCOL.md)), tool captures (June 2026).

## TL;DR (updated 2026-06-10)

1. **Zones:** external = **0x05**, internal = **0x01** (`Hazel.java`).
2. **Reads:** per-zone `10 83/85 00 <zone>`, fan `11 81 01 00`, firmware `00 81 00 00`, charging `05 85 00 00`, **all verified** on hardware.
3. **Writes:** Hazel two-packet format via `hazel_write.py`, **verified** (notify status `0x02`). Mouse-global keys **do not work**.
4. **Fans:** read `11 81`, write `11 01 01 00`, mirror `52401526` `05 39 XX`, **verified**.
5. **Firmware:** `01.00.09.00` (matches APK asset bundle).

Ground-truth sessions: **`captures/session-20260610-173104.log`**, effect wire-ID sweep (2026-06-10).

## Firmware effect wire ID sweep (0–15)

Device control → **Probe: firmware effect wire IDs 0–15**. Minimal/default payload per ID; **ACK `0x02` = accepted**, **`0x03` = rejected**. After a failed write, read-back still shows the **previous** effect, check `applied=yes` not just `read=`.

### Zone 0x05 (external fan rings)

| Wire ID | Write result | Applied (read body 0) | Notes |
|---------|--------------|------------------------|-------|
| 0 | ACK | yes → off | v3 off `00` |
| 1 | `0x03` | no | bare `01 00 00 00`, needs RGB (`01 00 00 01 RR GG BB`) |
| 2 | ACK | yes → breathing | `02 00 00 00` |
| 3 | ACK | yes → spectrum | `03 00 00 00` |
| 4 | ACK | yes → wave | `04 01 5A 00` |
| 5–15 | `0x03` | no | not implemented on firmware |

### Zone 0x01 (internal mouth)

| Wire ID | Write result | Applied | Notes |
|---------|--------------|---------|-------|
| 0 | ACK | yes → off | |
| 1 | `0x03` | no | bare static, needs RGB |
| 2 | ACK | yes → breathing | |
| 3 | ACK | yes → spectrum | |
| 4 | ACK | no | **wave rejected on internal** (APK: wave external-only) |
| 5–15 | `0x03` | no | not implemented |

**Conclusion:** Firmware supports wire IDs **0, 2, 3, 4 (external only), 1 with color**. IDs **5–15** are rejected, including **starlight (7)** even with full APK-style payloads (see Hazel extras below). Starlight is in shared decompiled code but **not** in the Zephyr app UI and **not** on retail hardware.

## Effect glossary (Hazel app)

| Effect | Wire ID | What it looks like | On Zephyr UI? |
|--------|---------|-------------------|---------------|
| **Breathing** | 2 | One or two colors pulse ↔ off | Yes (both zones) |
| **Starlight** | 7 | Random single-LED sparkles; optional 1–2 “anchor” colors | **No**, APK parser only; not in `zoneSupportedEffects` |
| **Audio reactive** | | Mic-driven; runs on **phone**, not firmware byte | No (shared app code with earbuds) |

**Voice amp / speakers:** **Project Hazel** and the announced **Zephyr Pro** had chin speaker grilles + mic for ~60 dB voice amplification ([The Verge CES 2022](https://www.theverge.com/2022/1/5/22855795/razer-zephyr-pro-mask-voice-amp-feature-price-ces-2022)). Razer **dropped voice amp from the shipped Zephyr** (weight/battery). The **Zephyr Pro was never released**. This repo targets the retail **Zephyr**, `Hazel.java` features are only `CHROMA_SETTINGS` and `FIRMWARE_UPDATE`; no speaker/volume Bluetooth commands in the APK. You will not find visible speaker grilles on the classic Zephyr like the Pro mockups.

## Hazel extras probe

Device control → **Probe: Hazel extras** sends:

- Firmware read `00 81 00 00`
- Brightness 64/128/255 on zones `0x05` and `0x01`
- Breathing: default, red, red+blue (external)
- Starlight: slow/medium/fast random, red sparkle, red+green (external)
- LED timeout: read `27 00 00` (3 B); then **30s test** via chroma `01 0B` packet and experimental Hazel `A7 00 01 1E`
- CLI prompts to wait ~35s, then **restore never** (`A7 00 01 00` + chroma timeout 0)

Firmware OTA: see [firmware-dfu.md](firmware-dfu.md) (Nordic DFU, not normal vendor writes).

### Hazel extras: session 2026-06-10 (firmware `01.00.09.00`)

| Probe | Result | Notes |
|-------|--------|-------|
| `firmware_read` | ACK | `01.00.09.00` |
| `brightness_*` (ext + int, 64/128/255) | ACK ×6 | Visible dimming, **confirmed on hardware** |
| `breathing_ext_default` | ACK | Default palette pulse |
| `breathing_ext_red` | ACK | `02 00 00 01 FF 00 00` |
| `breathing_ext_red_blue` | ACK | Two-color body |
| `starlight_ext_*` (all 5) | **0x03** ×5 | **Not supported** on retail Zephyr, wire ID 7 rejected even with full APK payloads |
| `timeout_get` `27 00 00` | **0x03** | Short-packet path rejected |
| `timeout_set_chroma_30s` `01 0B` | **0x03** | Chroma timeout not accepted |
| `timeout_set_hazel_raw_30` `A7 00 01 1E` | **0x03** | Hazel timeout not accepted (value 30 is not a valid app tier anyway, app uses 5/15/30/45/60 **minutes**) |
| `restore` never | **0x03** | Nothing to restore, set commands never applied |

**Starlight vs breathing:** Starlight probes run *after* breathing; failed starlight writes leave the previous effect active. Any brief pulse you noticed was almost certainly **breathing** (steps 8–10), not sparkles.

**LED timeout:** APK defines `A7`/`27` commands and the dashboard has a timeout row, but **this firmware rejects all timeout traffic** (`0x03`). Auto-off may be app-side only, a different transport, or unimplemented on shipped Zephyr. Do not expect 30s (or 5 min) auto-off via vendor writes until a working ACK is seen.

## Hardware verification matrix

| Command | Format | Session result |
|---------|--------|----------------|
| Sync reads (full Hazel set) | See [../docs/device-state.md](../docs/device-state.md) | OK, wave external, static internal, fan off |
| Listen fan mirror | `05 39` on `52401526` | OK, high→low→off sequence |
| `hazel_zone5_spectrum_apk` | `10 03 00 05` + `03 00 00 00` | ACK `0x02` |
| `hazel_zone5_breathing_apk` | `10 03 00 05` + `02 00 00 00` | ACK `0x02` |
| `hazel_zone5_off_apk` | `10 03 00 05` + `00` | ACK `0x02` |
| `hazel_zone5_wave_apk` | `10 03 00 05` + `04 01 5A 00` | ACK `0x02`, rate **90** matches factory read; old `32` (50) was too fast |
| `hazel_zone1_static_apk` | `10 03 00 01` + `01 00 00 01 RR GG BB` | ACK `0x02` |
| `hazel_zone1_off_apk` | `10 03 00 01` + `00` | ACK `0x02` |
| Legacy 10-byte internal bodies | `10 03 00 01` + 10 B | ACK `0x02` (also works) |
| `hazel_fan_apk` off/low/high | `11 01 01 00` + 6 B payload | ACK `0x02` |
| Mouse `10 03 00 00` static | Single/two packet | Reply `0x03` ready, **not OK** |
| Fan write `05 39` mirror prefix | Various | Status `0x05` or timeout, **not fan write** |

## Internal light (zone `0x01`): verified

**Read key:** `{req} 00 00 00 10 83 00 01`

**Read body (static on):** `01 01 00 01 00 FF 00 00 00 00` → on, green `#00FF00`.

**Write (preferred, APK):** two packets:

```text
{req} 07 00 00 10 03 00 01
01 00 00 01 {R} {G} {B} # static on

{req} 01 00 00 10 03 00 01
00 # off (v3)
```

**Write (legacy, also ACKs):** 10-byte zone marker still accepted:

```text
{req} 0A 00 00 10 03 00 01
01 01 00 01 {R} {G} {B} 00 00 00
```

Implemented in upstream tooling: `set_internal_light()`, [../docs/config/gatt_map.yaml](../docs/config/gatt_map.yaml), [config/probe_candidates.yaml](config/probe_candidates.yaml) → `internal_light`.

## External lighting (zone `0x05`): verified

**Read key:** `{req} 00 00 00 10 83 00 05`, returns effect type (e.g. wave + direction + rate).

**Wave speed:** payload byte 2 controls rotation speed; **higher = slower**. Factory unit read `0x5A` (90) before any tool writes. APK app slider maps to rate bytes 15 / 50 / 100 (documented, not fully hardware-swept on our unit). Changing wave in the Hazel app and capturing writes would verify direction and tier speeds.

**Write:** per-zone Hazel chroma (not mouse `10 03 00 00`):

```text
{req} {len} 00 00 10 03 00 05
{effect_config} # from createBleEffectrConfiguration
```

Static red example:

```text
30 07 00 00 10 03 00 05
01 00 00 01 FF 00 00
```

**Brightness write:**

```text
{req} 01 00 00 10 05 00 05
{level}
```

Mouse legacy `10 04 00 00` / `10 03 00 00`, replies `0x03` or `0x07`, not applied as OK.

## Rejected commands (do not use)

These were tried during research and **failed** on retail Zephyr hardware. For working commands, use [../docs/protocol.md](../docs/protocol.md) only.

### Mouse-global writes (`10 03 00 00`, `10 04 00 00`)

Command keys from Razer **mice** (last byte `00` = whole device, not a lighting zone). They appear in the Hazel APK because of shared Chroma code across Razer products. The Zephyr app uses per-zone keys (`10 03 00 05` / `01`) instead.

Sending mouse-global keys gets reply byte 7 = **`0x03`**, not **`0x02`**. Lights and fan do not change.

### Fan mirror write attempts (`05 39 …` on the write channel)

On status channel **`52401526`**, `05 39 XX` is a **read-only notification** when the physical fan button is pressed (`00` off, `01` low, `02` high). Research tried **writing** those bytes to the write channel; that does not control the fan (reply `0x05` or useless). Use write key **`11 01 01 00`** instead.

### Starlight (wire ID 7)

Present in shared decompiled code, **not** in the Zephyr app UI. All hardware probes returned **`0x03`**, including full APK-style payloads (Hazel extras session 2026-06-10).

### Wave direction RTL and app speed tiers

Factory default wave (`04 01 5A 00`, LTR) is **verified**. Right-to-left direction and APK tier bytes 15 / 50 / 100 are documented in the Hazel APK but were **not fully swept** on our test unit. Capture writes from the official app to confirm on your hardware.

## Fans: verified

| | Key / pattern |
|--|----------------|
| Read | `11 81 01 00` → byte 2 |
| Write | `11 01 01 00` then `01 00 {fan} 00 {fan} 00` |
| Mirror (read-only) | `52401526` `05 39 XX` |

Levels: `0` off, `1` low, `2` high.

## OpenSnek vs Zephyr

Same GATT service `52401523`, same framing (req, len, key, payload). Differences:

| | Mice (OpenSnek) | Zephyr (verified) |
|--|-----------------|-------------------|
| Extra notify | none | `52401526` |
| Lighting keys | global `10 83/03 00 00` | per-zone `10 83/03 00 05` / `01` |
| Write ACK | `0x02` | `0x02` for Hazel keys; `0x03` for mouse keys |
| Zone static marker | `00 00 01` | `01 00 01` on reads; writes use APK config bytes |
| Product | various | PnP `0x06340F01` |

## APK (`com.razer.hazel`)

Decompiled tree: `archive/apk/decompiled/sources/com/razer/audiocompanion/`

| File | Role |
|------|------|
| `model/devices/Hazel.java` | Zones, fan, brightness/effect apply |
| `model/effects/ChromaFirmwareEffectFactoryProtocol3.java` | Effect payloads |
| `model/effects/ChromaProtocolHelper.java` | Header bytes |

Dump APK-accurate hex: `python scripts/hazel_packet_dump.py --all`

## Tooling

| Action | Menu |
|--------|------|
| Full sync + listen | **[1] Read all + listen (30s)** |
| Set color / brightness / effect / internal / fan | **[3] Device control** (wave → speed prompt) |
| Send APK reference writes | **[2] Send reference codes** |
| Try write variants | **[2] Advanced probes** or [config/probe_candidates.yaml](config/probe_candidates.yaml) |
| Reference packet hex | `python scripts/hazel_packet_dump.py --all` |

Raw hex, internal on green (APK static):

```text
30 07 00 00 10 03 00 01
01 00 00 01 00 FF 00
```

Fan high:

```text
34 06 00 00 11 01 01 00
01 00 02 00 02 00
```
