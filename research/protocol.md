# Protocol — Razer Zephyr

Command table for **Razer Zephyr** (`com.razer.hazel`). See [device-state.md](device-state.md) for sync reference.

## Status legend

| Status | Meaning |
|--------|---------|
| unknown | Not yet captured |
| hypothesis | Guessed / not verified on Mac tool |
| verified | Confirmed on hardware or APK |

## Standard GATT (verified)

| Feature | Char UUID | Status |
|---------|-----------|--------|
| Battery | `0x2A19` | verified |
| Manufacturer | `0x2A29` | verified |
| PnP ID | `0x2A50` | verified |

## Vendor service `52401523` (verified)

| Char | UUID | Direction |
|------|------|-----------|
| Write | `52401524` | Host → mask |
| Notify | `52401525` | Mask → host (20 B) |
| Notify extra | `52401526` | Mask → host (8 B status) |

## Lighting zones (APK `Hazel.java`)

| Zone | ID | App name |
|------|-----|----------|
| External fan rings | `0x05` | `zone_name_external` |
| Internal mouth | `0x01` | `zone_name_internal` |

## Hardware verification

Session **`captures/session-20260610-173104.log`** (2026-06-10, Mac tool, `razer_probe` backend).

| Area | Result | Evidence |
|------|--------|----------|
| Full sync reads | **verified** | Battery, zones 5+1 brightness/chroma, fan read, charging |
| Fan listen mirror | **verified** | `52401526` `05 39` 02→01→00 during button presses |
| Hazel zone writes (external) | **verified** | Spectrum, breathing, off, wave — notify status `0x02` |
| Hazel zone writes (internal) | **verified** | APK static/off + legacy 10-byte bodies — status `0x02` |
| Fan write `11 01 01 00` | **verified** | Off/low/high payloads — status `0x02` |
| Mouse-global writes | **rejected** | `10 03 00 00` / `10 04` — status `0x03` ready, not `0x02` OK |
| Fan mirror guesses `05 39` write | **rejected** | Status `0x05` or silent — read-only mirror |

Success criterion for writes: `52401525` reply byte 7 = **`0x02`** (same as Hazel app `sendChunkedData` check).

Firmware version **`01.00.09.00`** in firmware-read continuation (`01 00 09 00`); matches asset `apk/.../hazel/01.00.09.00.zip`.

## Vendor read commands (sync)

| Feature | Key bytes | Status | Notes |
|---------|-----------|--------|-------|
| Zone brightness | `10 85 00 <zone>` | verified | Zones 5 + 1 |
| Zone chroma/effect | `10 83 00 <zone>` | verified | Effect byte 0 — see below |
| Fan speed | `11 81 01 00` | verified | Continuation byte **2**: 0/1/2 |
| Firmware | `00 81 00 00` | verified | Continuation bytes 0–3 → `MM.mm.bb.rr` |
| Charging | `05 85 00 00` | verified | Non-zero = charging |
| Battery (vendor) | `05 81 00 01` | verified | Prefer `0x2A19` |

### Hazel effect type (continuation byte 0)

This is the **firmware wire ID** (payload byte 0 in `createBleEffectrConfiguration`). It is **not** the same numbering as `EffectType` in the Hazel app enum (which goes up to 18 for audio-reactive / game modes).

| Wire ID | Name | APK sends? | Hardware sweep (2026-06-10) |
|---------|------|------------|------------------------------|
| 0 | off | yes | ACK both zones |
| 1 | static | yes (with RGB) | ACK when `01 00 00 01 RR GG BB`; bare `01 00 00 00` → `0x03` |
| 2 | breathing | yes | ACK both zones |
| 3 | spectrum | yes | ACK both zones |
| 4 | wave | yes | ACK **zone 0x05 only**; rejected on 0x01 |
| 5–6 | — | **no** | `0x03` rejected |
| 7 | starlight | yes | `0x03` with minimal probe payload |
| 8–15 | — | **no** | `0x03` rejected |

**How we know:** APK decompile (`ChromaFirmwareEffectFactoryProtocol3`, `Hazel.getEffectByZoneId`) only documents 0–4 and 7 on the wire. IDs 5, 6, 8+ might be ignored, misinterpreted, or do something undocumented — **only a hardware sweep confirms**.

**Discovery tool:** Device control → **Probe: firmware effect wire IDs 0–15** — writes minimal payload per ID, ACK check, then `10 83 00 <zone>` read-back. Watch the LEDs; ACK alone does not prove a visible effect.

Constants: `FIRMWARE_EFFECT_WIRE` in `hazel_write.py`.

### Effect visuals (Hazel app UI)

| Type | Name | What you see |
|------|------|--------------|
| 0 | off | Dark |
| 1 | static | Solid color (needs RGB write) |
| 2 | breathing | Colour ↔ off pulse |
| 3 | spectrum | Gradient colour cycle |
| 4 | wave | Rotating rainbow ring around fan LEDs |

### Wave payload (`04 {dir} {rate} 00`)

| Byte | Meaning |
|------|---------|
| 0 | `04` = wave |
| 1 | Direction: `1` = left→right, `2` = right→left |
| 2 | **Speed / rate** — **higher byte = slower rotation** |
| 3 | `00` padding |

**Factory default (verified):** rate **`90`** (`0x5A`) — read from device before probe writes in `captures/session-20260610-173104.log` (`04 01 5A 00`).

**APK write tiers** (`ChromaFirmwareEffectFactoryProtocol3.createBluetoothFirmwareEffectDataProtocol3`): Hazel maps app `Wave.rate` to only three BLE bytes when writing:

| App `Wave.rate` | BLE rate byte | Typical label |
|-----------------|---------------|---------------|
| `0` | `15` | slow |
| `100` (Hazel default object) | `50` | medium |
| `255` | `100` | fast |

The app speed slider uses `255 - Wave.rate` (`ChromaPickerUtils`, `speedSeekBar`). Firmware may store other values (e.g. factory `90`).

**Tool presets** (`hazel_write.py`): factory `90`, slow `15`, medium `50`, fast `100`. Device control → wave prompts for speed; reference menu wave uses factory `90`.

## Extra notify `52401526` (verified)

| Pattern | Meaning |
|---------|---------|
| `05 31 XX …` | Brightness mirror |
| `05 39 00` | Fan off |
| `05 39 01` | Fan low |
| `05 39 02` | Fan high |

## Vendor write commands (verified on hardware)

All writes go to **`52401524`** as **two ATT writes**: header (includes 24-bit payload length), then payload. Builders: `src/zephyr_re/protocol/hazel_write.py`, templates: `config/gatt_map.yaml`.

Regenerate reference hex:

```bash
python scripts/hazel_packet_dump.py --all
```

CLI menu **[3] Device control** uses the same builders (not the legacy mouse keys). **[2] Send reference codes** sends the table below one at a time.

### Reference writes (main menu [2] Send reference codes)

Order: wave → spectrum → breathing → off → static → brightness → internal → fans. Regenerate with `python scripts/hazel_packet_dump.py --all`.

| Command | write[2] payload | Notes |
|---------|------------------|-------|
| Wave, external `0x05` | `04 01 5A 00` | Rotating ring, **factory rate 90** |
| Spectrum, external `0x05` | `03 00 00 00` | Gradient cycle |
| Breathing, external `0x05` | `02 00 00 00` | Pulse |
| External off | `00` | v3 off (1 byte) |
| Static red, external `0x05` | `01 00 00 01 FF 00 00` | |
| Brightness 128, zone `0x05` | `80` | |
| Static green, internal `0x01` | `01 00 00 01 00 FF 00` | |
| Internal off | `00` | |
| Fan high / low / off | `01 00 n 00 n 00` | `n` = 2 / 1 / 0 |

### Write keys (summary)

| Feature | Header key | Payload | APK source |
|---------|------------|---------|------------|
| Zone effect / color | `10 03 00 <zone>` | `createBleEffectrConfiguration` | `ChromaFirmwareEffectFactoryProtocol3` |
| Zone off (v3) | `10 03 00 <zone>` | `00` (1 byte) | `ChromaProtocolHelper.createBluetoothOffEffectv3` |
| Zone off (firmware) | `10 03 00 <zone>` | `00 00 00 00` (4 bytes) | `createOffEffect` via `applyFirmwareEffect` |
| Zone brightness | `10 05 00 <zone>` | brightness u8 | `createBleSetBrightness` |
| Fan speed | `11 01 01 00` | `01 00 {fan} 00 {fan} 00` | `Hazel.createSetFanSpeed` |

Fan levels: `0` off, `1` low, `2` high.

Static color payload: effect type `01`, then `00 00 01 RR GG BB`.

## Frame format (52401525)

```
byte 0   request_id
byte 1   payload_length (0x00 for reads)
byte 2-3 reserved
byte 4-7 key (4 bytes)
byte 8+  payload or session token
byte 7   status (0x02 OK, 0x03 ready, 0x07 data)
```

Two-packet writes: header write, then payload write (OpenSnek / Hazel).

## Tool workflow

1. **Main menu [1]** — full Hazel read set + 30s listen
2. **Main menu [2]** — send reference Hazel writes (ACK = accepted)
3. **Main menu [3]** — device control (effects, brightness, fan, wave speed)
4. APK: `apk/decompiled/sources/.../Hazel.java`
5. `python scripts/hazel_packet_dump.py --all` — reference write hex
6. Session log: `captures/session-YYYYMMDD-HHMMSS.log`

## APK reference

- Package: `com.razer.hazel`
- Device class: `com.razer.audiocompanion.model.devices.Hazel`
- Decompiled tree: `apk/decompiled/`
