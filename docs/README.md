# Razer Zephyr documentation

How to control the mask over Bluetooth. Start with [bluetooth-basics.md](bluetooth-basics.md) if you are new to the protocol.

## How it works

| Doc | Purpose |
|-----|---------|
| [bluetooth-basics.md](bluetooth-basics.md) | Concepts: channels, UUIDs, hex, two-packet writes |
| [protocol.md](protocol.md) | API cheat sheet: read/write keys and payloads |
| [device-state.md](device-state.md) | Sync flow: read current fan, lights, battery |
| [features.md](features.md) | What the mask can do (fan + lighting zones) |

## For implementers

| Resource | Purpose |
|----------|---------|
| [config/gatt_map.yaml](config/gatt_map.yaml) | Machine-readable command templates |

## Research notes

Session logs, APK analysis, failed probes, and mouse protocol references live in **[../research/](../research/README.md)**. Not required to use the mask.
