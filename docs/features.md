# Zephyr features (Hazel app parity)

Verified against the retail Hazel APK UI and firmware `01.00.09.00`.

**Fan speed is not a lighting zone.** Zones `0x05` and `0x01` control **LEDs** only. The fan motor uses a separate command (`11 01 01 00` / `11 81 01 00`). See [protocol.md](protocol.md).

## 1. Fan speed

| Control | Notes |
|---------|--------|
| **Low** | Fan on, low speed |
| **High** | Fan on, high speed |
| **Off** | Dashboard toggle (not a sheet option in the app) |

## 2. Internal lighting (zone `0x01`)

| Effect | Colour options |
|--------|----------------|
| **Static** | Single colour |
| **Spectrum** | |
| **Breathing** | Single, bi-colour, or multi-colour |
| **Off** | Zone toggle off |

No wave on internal zone.

## 3. External lighting (zone `0x05`)

LEDs on the rings **around** the fans. This is not fan motor speed.

| Effect | Colour / options |
|--------|------------------|
| **Static** | Single colour |
| **Spectrum** | |
| **Breathing** | Single, bi-colour, or multi-colour |
| **Wave** | Direction (LTR/RTL) + speed |
| **Off** | Zone toggle off |
