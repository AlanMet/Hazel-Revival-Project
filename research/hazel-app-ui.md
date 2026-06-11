# Hazel app UI: what Zephyr should expose

Reconstructed from decompiled `com.razer.hazel` (`Hazel.java`, `DashboardActivity`, `ChromaInternalPresenter`, `SettingsFragment`). This is the **authoritative feature surface** for the retail Razer Zephyr, not the full shared earbuds/headset app.

**Live APK:** `archive/apk/com.razer.hazel.apk`, see upstream Hazel-Revival-Project for emulator setup scripts.

**RE rule of thumb:** if a feature is not in this app’s UI for Zephyr, deprioritize it (starlight, auto-shutoff, voice amp, etc.).

## Verified on emulator (Frida mock, 2026-06-10)

Connected dashboard exposes **three controllable rows** (each with an on/off toggle + options):

| Row | Toggle | Options when open |
|-----|--------|-------------------|
| **Fan speed** | Off = toggle off; on = fan running | **Low**, **High** only (no “off” in the sheet, off is the row toggle) |
| **Internal lighting** | Zone on/off | **Static**, **Spectrum**, **Breathing** (single / bi-colour / multi-colour) |
| **External lighting** | Zone on/off | **Static**, **Spectrum**, **Breathing** (single / bi-colour / multi-colour), **Wave** |

Wave sub-options (direction, speed) appear inside the external wave picker, not as separate dashboard rows.

Also on dashboard but not Bluetooth controls: **Buy Filters** (web link), **Firmware update** (when an update is available).

**Not in UI:** starlight, audio reactive, auto-shutoff, EQ, ANC, voice amp, speakers.

## Device profile (`Hazel.java`)

| Field | Value |
|-------|--------|
| App name | Zephyr (`device_name_hazel` = “Zephyr Wearable Air Purifier”) |
| `features` | **CHROMA_SETTINGS**, **FIRMWARE_UPDATE** only |
| Fan speeds | Off, Low, High |
| Lighting zones | `0x05` External, `0x01` Internal |
| Default effects | External: Wave LTR; Internal: Spectrum |
| Wave extras | Direction + speed (`PROPERTY_WAVE_DIRECTION`, `PROPERTY_WAVE_SPEED`) |
| Not in features | EQ, ANC, gaming mode, mic, smart link, range booster, speakers, voice amp |

---

## Dashboard (connected)

Presenters wired for Hazel: **Chroma**, **Battery**, **Fan**, **Firmware update**, **Notifications**, **Connectivity**.

```
┌─────────────────────────────────────┐
│ [Zephyr header / battery ring] │
├─────────────────────────────────────┤
│ Internal Lighting [ON] │ → Chroma picker (zone 0x01)
│ Spectrum / Static / … │
├─────────────────────────────────────┤
│ External Lighting [ON] │ → Chroma picker (zone 0x05)
│ Wave / Breathing / … │
├─────────────────────────────────────┤
│ Fan Speed [toggle]│ → Off via toggle; sheet = Low / High
├─────────────────────────────────────┤
│ Buy Filters [link] │ → Razer store (not BLE)
├─────────────────────────────────────┤
│ [Firmware update button] │ when update available
└─────────────────────────────────────┘
```

**Not on Hazel dashboard** (other Razer devices only): EQ, ANC, gaming mode, range booster, smart link, touch remap, auto-pause.

**Auto Shutoff row** (`timeoutParent` in layout) only appears if `TimeoutSettings` LiveData is populated, no Hazel-specific code path sets this in the decompiled tree; likely **never shown** or broken for Zephyr (matches our `0x03` on `27`/`A7`).

---

## Chroma picker (per zone)

Opened from dashboard row tap. `ChromaInternalPresenter.showPickerChromPicker()` passes `getSupportedEffectsByZoneId(zone)` from `Hazel.java`.

### External (`0x05`)

| Effect | In app UI | Firmware wire ID | Notes |
|--------|-----------|------------------|-------|
| Static | Yes | 1 | Color picker |
| Breathing | Yes | 2 | 1–2 colors in APK builder |
| Spectrum | Yes | 3 | |
| Wave | Yes | 4 | Direction LTR/RTL + speed tiers (slow/med/fast) |
| Starlight | **No** | 7 | Parser exists; not in `zoneSupportedEffects` |
| Wave dynamic | **No** | | Phone-side `EffectType.WaveDynamic` |
| Audio reactive | **No** | | Phone mic; not firmware |

Also: **brightness** slider per zone (default 255).

### Internal (`0x01`)

Same as external **except no Wave**, static, spectrum, breathing (single / bi / multi colour).

---

## Settings (gear menu)

Always present: Feedback, Customer support, About, Factory reset (staging builds).

When **connected** to Hazel:

| Item | Shown? | Notes |
|------|--------|-------|
| Firmware version | Yes | Read `00 81` |
| FAQ | Yes | `C.FAQ_REDIRECT` |
| Device connected / Forget | Yes | |
| Low power notification | If not enabled | Mask-specific copy |
| Master guide | Only if URL set | Hazel sets `null` |
| Auto Shutoff | **If** `sleepTimeout` LiveData fires | Earbud inheritance; rejected on our unit |
| Language / voice prompts | **No** | `supportedLanguage = null` |
| Range booster / autopause / fit test / tutorial | **No** | Removed when `noActiveDevice` or never populated for Hazel |

---

## Pairing / onboarding

- Pairing: hold multifunction **4s** until internal LEDs blink blue (`ct_pairing_string_msg_hazel`).
- Hazel-specific layouts: `fragment_pairing_instructions_hazel`, `fragment_notification_enable_hazel`.
- Battery notification onboarding uses Zephyr-specific strings.

---

## vs this tool (`zephyr_re`)

| Hazel app | Our CLI today | Gap |
|-----------|---------------|-----|
| External + internal chroma | Yes | |
| Wave direction + speed | Speed yes; direction in writes | |
| Breathing 2-color | Probe only | Could add to write menu |
| Brightness per zone | Yes | |
| Fan off (toggle) + low/high | Yes | Off = dashboard toggle, not sheet option |
| Breathing multi/bi colour | Probe only | Add to write menu |
| Firmware read | Yes (sync) | |
| Firmware OTA | Button in app | Documented only; dangerous |
| Auto shutoff | UI maybe; rejected on hardware | Host-side timer fallback |
| Buy filters | Web link | N/A |
| Battery low notify | Phone notification | N/A |

---

