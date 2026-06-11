# Device state — Razer Zephyr BLE

Public reference for **Main menu → [1] Read all + listen (30s)** and **Device control** writes. Keys and zones from **`com.razer.hazel`** APK plus hardware session **`captures/session-20260610-173104.log`** (2026-06-10).

## GATT services (verified)

| Service / char | UUID (short) | Role |
|----------------|--------------|------|
| Device Information | `0000180a` | Manufacturer `0x2A29`, PnP ID `0x2A50` |
| Battery | `0000180f` / `0x2A19` | Standard BLE battery % |
| Razer vendor | `52401523` | Vendor protocol service |
| Vendor write | `52401524` | Commands |
| Vendor notify | `52401525` | Primary replies (20-byte frames) |
| Vendor notify extra | `52401526` | Status mirror: brightness + fan |

## Lighting zones (APK)

| Zone ID | Name in app | Supported effects (UI) |
|---------|-------------|-------------------------|
| **0x05** | External (fan rings) | static, breathing, spectrum, **wave** |
| **0x01** | Internal (mouth) | static, breathing, spectrum |

Firmware effect type byte (continuation frame byte 0):

| ID | Name | Notes |
|----|------|-------|
| `0` | off | |
| `1` | static | RGB at bytes 4–6 |
| `2` | breathing | |
| `3` | spectrum | No fixed RGB |
| `4` | wave | Rotating rainbow ring; byte 1 = direction (`1` LTR, `2` RTL); byte 2 = rate (higher = slower) |
| `7` | starlight | APK parser only |

Wave read example: `04 01 5A 00` → wave LTR, rate **90** (factory default on tested unit).

## Sync flow

1. Read every readable GATT characteristic (includes `52401526` snapshot)
2. Hazel vendor reads (per zone + fan + firmware + charging)
3. Decode into `DeviceState`
4. Listen 30s — fan changes via `52401526` `05 39 XX`
5. Merge listen fan into state (`fan_speed_source: listen`)

## Vendor read keys (sync) — verified

| Field | Write (first packet) | Decode |
|-------|----------------------|--------|
| Ext brightness | `{req} 00 00 00 10 85 00 05` | Continuation byte 0 → 0–255 |
| Int brightness | `{req} 00 00 00 10 85 00 01` | Same |
| Ext effect/chroma | `{req} 00 00 00 10 83 00 05` | Body byte 0 = effect type |
| Int effect/chroma | `{req} 00 00 00 10 83 00 01` | Static: `01 01 00 01 RR GG BB …` |
| Fan speed | `{req} 00 00 00 11 81 01 00` | Continuation byte **2**: 0/1/2 |
| Firmware | `{req} 00 00 00 00 81 00 00` | Continuation bytes 0–3 → `01.00.09.00` |
| Charging | `{req} 00 00 00 05 85 00 00` | Non-zero = charging |

`{req}` = incrementing request id (tool starts at `0x30`).

## Fans — verified

| Path | Pattern | Levels |
|------|---------|--------|
| **Read** | `11 81 01 00` | Byte 2: 0 off, 1 low, 2 high |
| **Write** | `11 01 01 00` + `01 00 {n} 00 {n} 00` | Same levels; ACK `0x02` |
| **Mirror** | `52401526` `05 39 XX` | Live button changes (listen) |

Resolve order for display: vendor read → `52401526` GATT read → notify drain → assumed off.

## Vendor writes — verified (Hazel APK)

Two writes to `52401524`. ACK = notify byte 7 **`0x02`**.

| Feature | write[1] key | write[2] payload | Menu / API |
|---------|--------------|------------------|------------|
| External static color | `10 03 00 05` | `01 00 00 01 RR GG BB` | `set_external_color` |
| External effect | `10 03 00 05` | effect config bytes | `set_external_effect` — wave accepts `wave_rate` (default **90**) |
| External off (v3) | `10 03 00 05` | `00` | effect `off` |
| External brightness | `10 05 00 05` | `{level}` u8 | `set_external_brightness` |
| Internal static color | `10 03 00 01` | `01 00 00 01 RR GG BB` | `set_internal_light(on)` / menu **Write internal: static color** |
| Internal effect | `10 03 00 01` | effect config bytes | `set_internal_effect` — off / static / breathing / spectrum |
| Internal brightness | `10 05 00 01` | `{level}` u8 | `set_internal_brightness` |
| Internal off (v3) | `10 03 00 01` | `00` | `set_internal_light(off)` / **Write internal: off** |
| Fan off / low / high | `11 01 01 00` | `01 00 n 00 n 00` | `set_fan_speed` |

Reference hex (`python scripts/hazel_packet_dump.py --all`): [protocol.md](protocol.md#reference-writes-req-0x300x36).

**Do not use** mouse-global keys (`10 03 00 00`, `10 04 00 00`) — device replies `0x03` ready, not command OK.

## Extra notify `52401526` (verified)

| Pattern | Meaning |
|---------|---------|
| `05 31 XX …` | Brightness mirror |
| `05 39 XX …` | Fan level (0/1/2) |

## Session log example (2026-06-10)

From `captures/session-20260610-173104.log` after sync + fan button listen:

```
battery: 100%
ext brightness: 100% (zone 0x05), raw 0xFF
int brightness: 100% (zone 0x01)
external color: — (wave (LTR, rate 90))
external effect: wave
internal effect: static
fans: off (listen)          # was off (read); listen saw 02→01→00
internal light: on #00FF00, zone 0x01
firmware: 01.00.09.00
charging: no
```

Probe highlights (same session): Hazel external effects 1–4 ACK; all internal light candidates ACK; `hazel_fan_apk` off/low/high ACK; legacy mouse + `05 39` write guesses failed.

## LED auto-shutoff (timeout)

The Hazel dashboard can show **Auto Shutoff** (`auto_shutoff` string) — turn off lighting after N minutes to save battery (Razer quoted ~8h without lights vs ~3.5h with Chroma + high fan).

| Path | Packets | Firmware `01.00.09.00` |
|------|---------|------------------------|
| Hazel | get `27 00 00`, set `A7 00 01 {minutes}` (0 / 5 / 15 / 30 / 45 / 60) | **0x03 rejected** (session 2026-06-10) |
| Chroma | set `01 0B` (14-byte timeout frame) | **0x03 rejected** |
| Vendor reads | `05 84` power timeout, `05 82` sleep timeout | Not yet verified on Zephyr |

APK defines the Hazel commands but `setTimeoutValue` may never run for Zephyr in practice — inherited from the shared earbuds/headset app.

**If BLE timeout stays dead:** implement **host-side auto-off** in this tool (timer while connected → write both zones off). That preserves battery behavior for desktop use but does not persist after disconnect (unlike firmware-side shutoff).

## Implementation

| Piece | Path |
|-------|------|
| Parsers | `reverse-engineering/src/zephyr_re_dev/protocol/zephyr_parse.py` |
| Write builders | `reverse-engineering/src/zephyr_re_dev/protocol/hazel_write.py` · `reverse-engineering/zephyr_re/protocol/packets.py` |
| Backend | `reverse-engineering/src/zephyr_re_dev/protocol/razer_vendor.py` |
| State | `reverse-engineering/src/zephyr_re_dev/device/state.py` |
| GATT templates | `reverse-engineering/tools/config/gatt_map.yaml` |
