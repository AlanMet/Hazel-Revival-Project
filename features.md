# Zephyr features (Hazel app parity)

Verified against the retail Hazel APK UI and firmware `01.00.09.00`.

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
| **Spectrum** | — |
| **Breathing** | Single, bi-colour, or multi-colour |
| **Off** | Zone toggle off |

No wave on internal zone.

## 3. External lighting (zone `0x05`)

| Effect | Colour / options |
|--------|------------------|
| **Static** | Single colour |
| **Spectrum** | — |
| **Breathing** | Single, bi-colour, or multi-colour |
| **Wave** | Direction (LTR/RTL) + speed |
| **Off** | Zone toggle off |
