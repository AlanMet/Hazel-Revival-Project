# How the Zephyr talks over Bluetooth

This page explains the Bluetooth side of controlling the mask. You do **not** need a networking or electronics background. Read this before the command tables in [protocol.md](protocol.md).

## What Bluetooth is doing here

The Razer Zephyr is a **Bluetooth device**, like wireless headphones or a fitness tracker. Your phone or computer is the **controller**; the mask is the **device being controlled**.

```
  Your phone / computer                    Razer Zephyr
  (controller)                             (mask)
       │                                        │
       │  wireless link (Bluetooth)             │
       └────────────────────────────────────────┘
```

There is no Wi‑Fi, no cloud, and no Razer account in the path we care about. The Hazel app (and our replacement apps) talk **directly** to the mask once it is paired.

### Pairing vs connecting


| Step           | What it means                                                                                             |
| -------------- | --------------------------------------------------------------------------------------------------------- |
| **Pairing**    | Done once in your OS Bluetooth settings. The mask and your computer/phone remember each other.            |
| **Connecting** | The app opens a live link to send commands (fan speed, lights). You do this inside the app after pairing. |


If pairing works but the app cannot connect, the problem is usually in the app, not in system settings.

## How data is organized on the mask

Bluetooth devices expose their features as a small tree of **services** (folders) and **channels** (files inside each folder). Each line below has a **UUID**, a 36-character id that software uses to open the right folder or channel.

```
Mask
├── Standard battery service       (00002a19 …)  ← battery %
├── Standard device-info service   (0000180a …)  ← manufacturer name, model id
└── Razer vendor service           (52401523 …)  ← fan + lighting (the important one)
    ├── write channel              (52401524 …)  ← you send commands here
    ├── reply channel              (52401525 …)  ← mask sends answers (20 bytes)
    └── status channel             (52401526 …)  ← mask pushes live updates (8 bytes)
```

The `…` means the UUID continues. See the next section for the full strings.

### The UUID system

Every line in the tree has its own UUID. Software does not open “write channel” by name. It opens `52401524-F97C-7F90-0E7F-6C6F4E36DB1C`. The names in the tree are for humans; the UUIDs are what the Bluetooth stack actually uses.

For the **Razer vendor** branch (the block we care about for fan and lights), the full UUIDs are:


| Name in the tree above | Full UUID                              |
| ---------------------- | -------------------------------------- |
| Razer vendor service   | `52401523-F97C-7F90-0E7F-6C6F4E36DB1C` |
| write channel          | `52401524-F97C-7F90-0E7F-6C6F4E36DB1C` |
| reply channel          | `52401525-F97C-7F90-0E7F-6C6F4E36DB1C` |
| status channel         | `52401526-F97C-7F90-0E7F-6C6F4E36DB1C` |


Notice the pattern: only the first 8 characters change (`52401523` → `52401524` → `52401525` → `52401526`). The back half (`-F97C-7F90-0E7F-6C6F4E36DB1C`) is identical on all four. Repeating the full string in every table would be unreadable, so in this documentation we shorten to those **first 8 characters**, the same short forms shown in parentheses in the tree.

> **Critical rule for developers:** Short forms like `52401524` are for reading docs only. Your code must use the **full 36-character strings**. The Bluetooth hardware layer does not accept the short forms. Your app will fail to connect if the tail is missing.

### Standard vs vendor service


| Kind                  | What it is                                                        | On the Zephyr                                                              |
| --------------------- | ----------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **Standard services** | Defined by Bluetooth for all devices (battery, device name, etc.) | Top two lines in the tree: battery level, “Razer Inc.” manufacturer string |
| **Vendor service**    | Custom to the manufacturer, not documented publicly               | The **`52401523`** branch: all fan and lighting control                |


Reverse engineering mostly means figuring out **what bytes to send** on the **write channel** (`52401524`), and **how to read** the **reply channel** (`52401525`) and **status channel** (`52401526`).

<a id="write-channel"></a>
<a id="reply-channel"></a>

### What each Razer channel does


| Name in tree   | UUID (short) | Direction  | Purpose                                                   |
| -------------- | ------------ | ---------- | --------------------------------------------------------- |
| write channel  | `52401524`   | You → mask | Send a command (change fan, set colour, etc.)             |
| reply channel  | `52401525`   | Mask → you | Mask answers: “OK” or error, plus data (20-byte messages) |
| status channel | `52401526`   | Mask → you | Live updates, e.g. fan level changed on the mask button   |


**Write** = you push bytes in.  
**Notify** = the mask can push bytes to you without being asked (or right after a command as a reply). The reply and status channels work this way. You subscribe to them when the app connects, same as the original Hazel app.

## Commands are bytes (hex)

Commands are not English text. They are **raw bytes**, written in **hex** in our docs. Each pair (e.g. `FF`) is one byte (0–255).

<a id="two-packet-write-rule"></a>

## The two-packet write rule

To **change** something on the mask (fan speed, colour, brightness, effect), you almost always send **two separate writes** to the **write channel** (`52401524`). You never combine them into one write.

| Step | What you send | What it contains |
|------|---------------|------------------|
| **1. Header packet** | First write to `52401524` | Request id, payload length, and a 4-byte **key** (what command this is) |
| **2. Payload packet** | Second write to `52401524` | The **data** for that command (colour bytes, fan level, effect id, etc.) |

After both writes, the mask sends a **reply** on the **reply channel** (`52401525`). Byte 7 = **`0x02`** means the command was accepted.

**Reads** (asking for current fan speed, battery, etc.) also go out on the write channel, but usually as a single header packet with a read key. The answer still comes back on the reply channel.

The tables in [protocol.md](protocol.md) list the **4-byte keys** and **payload bytes**. The worked example below shows how those fit into full 8-byte header packets.

### Worked example: set external lighting to solid red

Both lines below are **sent by the app to the mask** on the **write channel** (`52401524`). Nothing in this block is something the mask sends the app.

```
  YOUR APP                                    MASK
     |                                          |
     |  -> write packet 1 (header) -----------> |
     |     30 07 00 00 10 03 00 05              |
     |                                          |
     |  -> write packet 2 (payload) -----------> |
     |     01 00 00 01 FF 00 00                 |
     |                                          |
     |  <- reply (20 bytes on 52401525) -------- |
     |     byte 7 = 0x02 means "accepted"       |
```

**Packet 1 is the header.** It says *what kind* of command is coming and how long the follow-up is:

```text
30 07 00 00 10 03 00 05
│  └─────┘ └─────────┘
│  length   key (4 bytes)
request id
```


| Bytes | Hex           | Meaning                                                                                     |
| ----- | ------------- | ------------------------------------------------------------------------------------------- |
| 0     | `30`          | **Request id** (sequence number for this command; tools often start at `0x30` and count up) |
| 1–3   | `07 00 00`    | **Payload length** (3 bytes, little-endian): the next packet will be **7 bytes** long       |
| 4–7   | `10 03 00 05` | **Key**: “set zone effect” on zone **`0x05`** (external fan rings) |

The **`0x05` is not the request id.** It is the **last byte of the key** (byte index **7** in this 8-byte header). The request id is only byte **0** (`30` here).

```text
Byte index:  0    1    2    3    4    5    6    7
             30   07   00   00   10   03   00   05
             │    └─ payload length ─┘    └── key ──┘
             │                              └── zone id (0x05 = external)
             └── request id (0x30)
```

Same idea for internal lighting: the key ends in **`01`** instead, e.g. `10 03 00 01`.


**Packet 2 is the payload.** It says *what to do* for that key:

```text
01 00 00 01 FF 00 00
│  └─────┘ └─────┘
│  marker   RGB colour
effect type
```


| Bytes | Hex        | Meaning                                   |
| ----- | ---------- | ----------------------------------------- |
| 0     | `01`       | **Effect type**: static (solid colour)    |
| 1–3   | `00 00 01` | Required marker for a static colour write |
| 4–6   | `FF 00 00` | **Colour**: red (`RR GG BB`)              |


Together, the two packets mean: **external lighting → static red**.

Other actions use the same header shape with different keys and payloads. Examples: fan speed uses key `11 01 01 00`; brightness uses `10 05 00 05` with a single-byte payload. Full tables: [protocol.md](protocol.md).

### What the mask sends back (receive)

After you send both packets, the mask answers on the **reply channel** (`52401525`), not on the write channel. That message is **20 bytes** and uses a similar layout (request id, length, key, data), but **you read it**, you do not send it.

For a successful command, **byte 7** of that reply is **`0x02`**. If you see **`0x03`**, the mask rejected the command (wrong key, bad payload, wrong zone, etc.).

Replies are harder to read than commands because they can include session data and vary by command type. For now, treat **`0x02` at byte 7** as the main thing to check after a write.

**Reads** follow the same pattern: you **send** on the write channel, then **receive** the answer on the reply channel. See [device-state.md](device-state.md).

## How you know a command worked

After a write, the mask sends a reply on **`52401525`**. Byte 7 of that reply is a **status code**:

| Byte 7 | Meaning |
|--------|---------|
| **`0x02`** | Command accepted (same check the Hazel app uses) |
| **`0x03`** | Not accepted (wrong command for this device, or bad payload) |


If you see `0x02`, the mask understood the command. That does not always mean the LEDs look different (some payloads need colour bytes, etc.), but it is the protocol-level “OK”.

## Lighting zones

The mask has two separate LED areas. Each has a **zone id** that goes in the **last byte of the 4-byte key** in the header packet (byte index 7 in a standard 8-byte header). It is not the request id (byte 0) and not part of the payload packet unless the command itself is about an effect type (see below).

| Zone id | Where on the mask | In the Hazel app | Example key (last 4 bytes) |
|---------|-------------------|------------------|----------------------------|
| **`0x05`** | External, rings around the fans | “External lighting” | `10 03 00 05` |
| **`0x01`** | Internal, mouth area | “Internal lighting” | `10 03 00 01` |

**Do not confuse zone ids with other `0x01` / `0x05` bytes in a message:**

| Value | Meaning | Where it appears |
|-------|---------|------------------|
| `0x05` | External **zone** | Last byte of key, e.g. `10 03 00 **05**` |
| `0x01` | Internal **zone** | Last byte of key, e.g. `10 03 00 **01**` |
| `0x01` | Fan **low** | Payload of fan write, e.g. `01 00 **01** 00 01 00` |
| `0x01` | **Static** effect | First byte of effect payload, e.g. `**01** 00 00 01 FF 00 00` |
| `0x30` | **Request id** (example) | Byte 0 of header only, increments per command |

## Fan levels

Fan speed is a number in commands and status updates:


| Value | Speed |
| ----- | ----- |
| `0`   | Off   |
| `1`   | Low   |
| `2`   | High  |


If you press the physical button on the mask, the **status channel** (`52401526`) pushes an update with pattern `05 39 XX` where `XX` is 0, 1, or 2. Apps can listen for that to stay in sync.

## What we reverse-engineered

We did not get a manual from Razer. We learned this by:

1. **Decompiling the Hazel Android app**: see which bytes it sends
2. **Capturing traffic** while using the app or our tools with a real mask
3. **Trying commands on hardware** and checking replies (`0x02` vs `0x03`)

Findings are marked **verified**, **hypothesis**, or **rejected** in the other docs.

## Words we avoid (and what we say instead)


| Jargon              | Plain language                                                |
| ------------------- | ------------------------------------------------------------- |
| BLE                 | Bluetooth (Low Energy). Just “Bluetooth” is fine.             |
| GATT                | The service/characteristic layout described above             |
| Host                | Your phone or computer                                        |
| Peripheral          | The mask                                                      |
| Characteristic      | A single read/write/notify channel (write, reply, status)     |
| ATT write           | Sending a packet on the write channel                         |
| Notify subscription | Letting the app receive replies and live status from the mask |


**UI**, **UUID**, and **hex** are fine. They are either everyday (UI) or defined above (UUID, hex).

## Next steps


| If you want to…                          | Read                                                            |
| ---------------------------------------- | --------------------------------------------------------------- |
| See every command byte                   | [protocol.md](protocol.md)                                      |
| Understand “sync” and current mask state | [device-state.md](device-state.md)                              |
| See what the mask can do                 | [features.md](features.md)                                      |
| How we figured this out (research)       | [../research/](../research/README.md)                           |


