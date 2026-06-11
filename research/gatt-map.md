# Bluetooth map: Razer Zephyr

List of services and channels on the mask, plus connect snapshots from research tools.

> **Control the mask:** [../docs/bluetooth-basics.md](../docs/bluetooth-basics.md)

## How to use

1. Connect to the mask via the tool
2. Each connect appends a **Snapshot** section below with full service/characteristic list
3. Copy vendor UUIDs into [../docs/config/gatt_map.yaml](../docs/config/gatt_map.yaml)

## Expected (hypothesis)

Razer mice use vendor service `52401523-F97C-7F90-0E7F-6C6F4E36DB1C`. The Zephyr may use the same or a custom UUID, verify with GATT explorer.

## Manual notes

| Field | UUID | Notes |
|-------|------|-------|
| Service | `52401523-F97C-7F90-0E7F-6C6F4E36DB1C` | Same vendor service UUID as Razer mice (OpenSnek) |
| Write char | `52401524-F97C-7F90-0E7F-6C6F4E36DB1C` | |
| Notify char | `52401525-F97C-7F90-0E7F-6C6F4E36DB1C` | |
| Extra notify | `52401526-F97C-7F90-0E7F-6C6F4E36DB1C` | Zephyr-only |
| Battery (standard) | `00002a19-0000-1000-8000-00805f9b34fb` | BAS |

### Hazel protocol (verified 2026-06-10)

Hardware session: `captures/session-20260610-173104.log`, sync reads, fan listen, Hazel writes ACK `0x02`.

| Doc | Contents |
|-----|----------|
| [../docs/protocol.md](../docs/protocol.md) | Read/write keys and payloads |
| [../docs/device-state.md](../docs/device-state.md) | Sync flow |
| [research-findings.md](research-findings.md) | Probe results, OpenSnek vs Zephyr |
| [firmware-dfu.md](firmware-dfu.md) | OTA / Nordic DFU (not vendor lighting) |
| [hazel-app-ui.md](hazel-app-ui.md) | Official app UI surface (from APK) |

```bash
python archive/tools/hazel_packet_dump.py --all # when ported from upstream
```

Templates: [../docs/config/gatt_map.yaml](../docs/config/gatt_map.yaml)

---

<!-- Snapshots appended automatically on connect -->

## Snapshot 2026-06-10T15:12:05.673282+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T15:48:31.879174+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T15:59:57.676687+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:04:52.343480+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:06:42.282039+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:09:41.242351+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:11:49.317660+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:14:33.574088+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:18:54.578662+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:23:47.942216+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:27:29.363813+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:29:32.756063+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:31:02.309290+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:38:40.233969+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:46:54.891228+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:53:17.581708+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T16:56:29.242486+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:29:01.607082+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:31:08.555750+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:37:15.857565+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:40:13.055778+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:40:52.550576+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:43:06.576289+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:45:40.716402+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:49:15.073881+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T17:57:52.632781+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]

## Snapshot 2026-06-10T18:14:16.406555+00:00
Address: `1D29E6F5-E567-3608-2C0F-F08E522E6763`

### Service `0000180a-0000-1000-8000-00805f9b34fb`
- `00002a29-0000-1000-8000-00805f9b34fb` handle=15 [read]
- `00002a50-0000-1000-8000-00805f9b34fb` handle=17 [read]

### Service `0000180f-0000-1000-8000-00805f9b34fb`
- `00002a19-0000-1000-8000-00805f9b34fb` handle=20 [read, notify]

### Service `52401523-f97c-7f90-0e7f-6c6f4e36db1c`
- `52401524-f97c-7f90-0e7f-6c6f4e36db1c` handle=35 [write]
- `52401525-f97c-7f90-0e7f-6c6f4e36db1c` handle=37 [read, notify]
- `52401526-f97c-7f90-0e7f-6c6f4e36db1c` handle=40 [read, notify]
