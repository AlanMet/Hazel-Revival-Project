# Research notes

How the Zephyr protocol was reverse-engineered. Session captures, probe results, and reference material that did not make it into the main docs.

**To control the mask**, use **[../docs/](../docs/README.md)** only.

## Findings

| Doc | Contents |
|-----|----------|
| [research-findings.md](research-findings.md) | Hardware verification, rejected commands, effect sweeps |
| [hazel-app-ui.md](hazel-app-ui.md) | Retail Hazel app UI (APK decompile) |
| [firmware-dfu.md](firmware-dfu.md) | OTA / Nordic DFU (not day-to-day control) |

## Captures and maps

| Doc | Contents |
|-----|----------|
| [gatt-map.md](gatt-map.md) | Service UUIDs and connect snapshots |
| [gatt-reads.md](gatt-reads.md) | Raw GATT read logs |

## External reference

| Doc | Contents |
|-----|----------|
| [opensnek-BLE_PROTOCOL.md](opensnek-BLE_PROTOCOL.md) | Razer mouse protocol (shared vendor service shape) |

## Probe configs

| File | Contents |
|------|----------|
| [config/probe_candidates.yaml](config/probe_candidates.yaml) | Experimental write variants used during research |

Session logs and APK binaries: [`../archive/`](../archive/)
