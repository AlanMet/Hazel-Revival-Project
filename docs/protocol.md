# Protocol specification: Razer Zephyr

Verified hex byte structures for controlling the mask (`com.razer.hazel`, firmware `01.00.09.00`).

**Prerequisite:** Read [bluetooth-basics.md](bluetooth-basics.md) first. You need the [write channel (`52401524`)](bluetooth-basics.md#write-channel), [reply channel (`52401525`)](bluetooth-basics.md#reply-channel), and [two-packet write rule](bluetooth-basics.md#two-packet-write-rule).

**Research notes** (verification sessions, failed probes): [../research/](../research/README.md).

**Machine-readable templates:** [config/gatt_map.yaml](config/gatt_map.yaml).

---

## 1. Zone and value dictionaries

Reference these once when building packets.

### Hardware zones


| ID     | Location              |
| ------ | --------------------- |
| `0x05` | External rings (fans) |
| `0x01` | Internal area (mouth) |


### Fan power levels


| Value  | Speed |
| ------ | ----- |
| `0x00` | Off   |
| `0x01` | Low   |
| `0x02` | High  |


### Lighting effect IDs (payload byte 0)


| ID     | Effect         | Notes                            |
| ------ | -------------- | -------------------------------- |
| `0x00` | Off            | Payload can be single byte `00`  |
| `0x01` | Static colour  | Requires RGB payload (see below) |
| `0x02` | Breathing      |                                  |
| `0x03` | Spectrum cycle |                                  |
| `0x04` | Wave           | **External zone `0x05` only**    |


Starlight (wire ID 7) is **not supported** on retail Zephyr.

---

## 2. Read commands (querying state)

Send a read on the **write channel** (`52401524`). The mask answers on the **reply channel** (`52401525`).

Each read uses an 8-byte header packet (request id + length + 4-byte key). See [bluetooth-basics.md](bluetooth-basics.md) for the full header layout. The **key** is the last four bytes:


| Feature              | Read key (4 bytes) | Answer location in reply                              |
| -------------------- | ------------------ | ----------------------------------------------------- |
| Battery %            | `05 81 00 01`      | Prefer standard service `0x2A19` instead              |
| Fan speed            | `11 81 01 00`      | Payload byte 2 (`0` / `1` / `2`)                      |
| Charging status      | `05 85 00 00`      | Non-zero = plugged in                                 |
| Firmware version     | `00 81 00 00`      | Payload bytes 0–3 → `MM.mm.bb.rr`                     |
| Zone brightness      | `10 85 00 <zone>`  | Payload byte 0 (0–255)                                |
| Zone effect / colour | `10 83 00 <zone>`  | Payload byte 0 = effect ID; static includes RGB bytes |


---

## 3. Write commands (two-packet sequence)

Send **header packet**, then **payload packet**, both on the write channel (`52401524`).

Tables below show the **4-byte header key** and **payload bytes**. Wrap the key in the standard 8-byte header (request id + 3-byte little-endian length). Full worked example: [bluetooth-basics.md](bluetooth-basics.md#worked-example-set-external-lighting-to-solid-red).

**Success:** reply on `52401525`, byte 7 = `0x02`.

### Fan speed control


|            | Bytes                         |
| ---------- | ----------------------------- |
| Header key | `11 01 01 00`                 |
| Payload    | `01 00 [level] 00 [level] 00` |


Example (high): `01 00 02 00 02 00`

### Zone brightness (0–255)


|            | Bytes             |
| ---------- | ----------------- |
| Header key | `10 05 00 <zone>` |
| Payload    | `[brightness]`    |


Example (external 50% / 128): key `10 05 00 05`, payload `80`

### Turn zone off


|            | Bytes             |
| ---------- | ----------------- |
| Header key | `10 03 00 <zone>` |
| Payload    | `00`              |


### Set lighting effect (standard)


|            | Bytes                  |
| ---------- | ---------------------- |
| Header key | `10 03 00 <zone>`      |
| Payload    | `[effect_id] 00 00 00` |


Examples:


| Effect    | Zone            | Payload       |
| --------- | --------------- | ------------- |
| Breathing | internal `0x01` | `02 00 00 00` |
| Spectrum  | external `0x05` | `03 00 00 00` |


### Set lighting effect (static RGB)


|            | Bytes                     |
| ---------- | ------------------------- |
| Header key | `10 03 00 <zone>`         |
| Payload    | `01 00 00 01 [R] [G] [B]` |


Example (external solid red): key `10 03 00 05`, payload `01 00 00 01 FF 00 00`

### Set lighting effect (wave)

Wave works on **external zone `0x05` only**. Higher speed byte = slower rotation.


|            | Bytes                       |
| ---------- | --------------------------- |
| Header key | `10 03 00 05`               |
| Payload    | `04 [direction] [speed] 00` |



| Field     | Values                                                              |
| --------- | ------------------------------------------------------------------- |
| Direction | `01` left→right, `02` right→left                                    |
| Speed     | `15` fast, `50` medium, `90` factory default (verified), `100` slow |


Example (factory default wave): payload `04 01 5A 00`

RTL direction and tier speeds 15/50/100 are documented in the Hazel APK; not fully hardware-swept on our test unit. Details: [../research/research-findings.md](../research/research-findings.md).

---

## 4. Status channel (listen only)

Channel `52401526` pushes live updates. **Do not** send these bytes on the write channel.


| Pattern      | Meaning           |
| ------------ | ----------------- |
| `05 39 00`   | Fan off           |
| `05 39 01`   | Fan low           |
| `05 39 02`   | Fan high          |
| `05 31 XX …` | Brightness mirror |


