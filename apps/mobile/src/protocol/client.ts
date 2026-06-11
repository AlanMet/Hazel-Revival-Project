import {
  BATTERY_CHAR_UUID,
  EXTERNAL_LIGHT_ZONE,
  INTERNAL_LIGHT_ZONE,
  NOTIFY_TIMEOUT_MS,
  REQUEST_ID_START,
  type FanSpeed,
} from "./constants.js";
import {
  buildReadHeader,
  effectPackets,
  fanSpeedPackets,
  KEY_READ_CHARGING,
  KEY_READ_FAN,
  KEY_READ_FIRMWARE,
  ZONE_EFFECT_KEY,
  type EffectName,
  type EffectOptions,
} from "./packets.js";
import {
  parseCharging,
  parseEffect,
  parseExtraFan,
  parseFanRead,
  parseFirmware,
  writeAck,
  type DeviceState,
} from "./parse.js";
import {
  BleTransport,
  RAZER_VENDOR_NOTIFY,
  RAZER_VENDOR_NOTIFY_EXTRA,
  RAZER_VENDOR_WRITE,
} from "../ble/transport.js";

const VENDOR_READ_GAP_MS = 150;

export class ZephyrClient {
  private transport = new BleTransport();
  private reqId = REQUEST_ID_START;
  private state: DeviceState | null = null;
  private onFanChange: ((speed: FanSpeed) => void) | null = null;

  async initialize(): Promise<void> {
    await this.transport.initialize();
    this.transport.onNotify(RAZER_VENDOR_NOTIFY_EXTRA, (view) => {
      const data = dataViewToBytes(view);
      const speed = parseExtraFan(data);
      if (speed && this.state) {
        this.state.fanSpeed = speed;
        this.state.fanSpeedSource = "notify";
        this.onFanChange?.(speed);
      }
    });
  }

  get lastState(): DeviceState | null {
    return this.state;
  }

  setFanNotifyHandler(cb: ((speed: FanSpeed) => void) | null): void {
    this.onFanChange = cb;
  }

  async scan(timeoutMs = 8000) {
    return this.transport.scan(timeoutMs);
  }

  async connect(deviceId: string): Promise<void> {
    await this.transport.connect(deviceId);
    this.state = await this.syncState();
  }

  async disconnect(): Promise<void> {
    await this.transport.disconnect();
    this.state = null;
  }

  private nextReqId(): number {
    const id = this.reqId;
    this.reqId = (this.reqId + 1) & 0xff;
    return id;
  }

  private async vendorRead(key: number[]): Promise<Uint8Array[]> {
    const header = buildReadHeader(this.nextReqId(), key);
    const frames: Uint8Array[] = [];
    await this.transport.write(RAZER_VENDOR_WRITE, header);
    return this.transport.waitForNotify(RAZER_VENDOR_NOTIFY, NOTIFY_TIMEOUT_MS, frames);
  }

  private async sendPair(header: Uint8Array, payload: Uint8Array): Promise<boolean> {
    const frames: Uint8Array[] = [];
    await this.transport.write(RAZER_VENDOR_WRITE, header);
    await this.transport.write(RAZER_VENDOR_WRITE, payload);
    await this.transport.waitForNotify(RAZER_VENDOR_NOTIFY, NOTIFY_TIMEOUT_MS, frames);
    return writeAck(frames);
  }

  async syncState(): Promise<DeviceState> {
    const batteryPct = await this.transport.readBattery();

    await sleep(VENDOR_READ_GAP_MS);
    const effectExternal = await this.vendorRead(ZONE_EFFECT_KEY(EXTERNAL_LIGHT_ZONE));
    await sleep(VENDOR_READ_GAP_MS);
    const effectInternal = await this.vendorRead(ZONE_EFFECT_KEY(INTERNAL_LIGHT_ZONE));
    await sleep(VENDOR_READ_GAP_MS);
    const fanFrames = await this.vendorRead(KEY_READ_FAN);
    await sleep(VENDOR_READ_GAP_MS);
    const firmwareFrames = await this.vendorRead(KEY_READ_FIRMWARE);
    await sleep(VENDOR_READ_GAP_MS);
    const chargingFrames = await this.vendorRead(KEY_READ_CHARGING);

    const fanSpeed = parseFanRead(fanFrames) ?? "off";

    this.state = {
      batteryPercent: batteryPct,
      fanSpeed,
      fanSpeedSource: "read",
      externalEffect: parseEffect(effectExternal),
      internalEffect: parseEffect(effectInternal),
      firmwareVersion: parseFirmware(firmwareFrames),
      isCharging: parseCharging(chargingFrames),
    };
    return this.state;
  }

  async setFanSpeed(speed: FanSpeed): Promise<boolean> {
    const [header, payload] = fanSpeedPackets(this.nextReqId(), speed);
    return this.sendPair(header, payload);
  }

  async setEffect(zone: number, effect: EffectName, opts: EffectOptions = {}): Promise<boolean> {
    const [header, payload] = effectPackets(this.nextReqId(), effect, zone, opts);
    return this.sendPair(header, payload);
  }

  async fanOff(): Promise<boolean> {
    return this.setFanSpeed("off");
  }
  async fanLow(): Promise<boolean> {
    return this.setFanSpeed("low");
  }
  async fanHigh(): Promise<boolean> {
    return this.setFanSpeed("high");
  }

  async internalStatic(r: number, g: number, b: number): Promise<boolean> {
    return this.setEffect(INTERNAL_LIGHT_ZONE, "static", { r, g, b });
  }
  async internalSpectrum(): Promise<boolean> {
    return this.setEffect(INTERNAL_LIGHT_ZONE, "spectrum");
  }
  async internalBreathing(): Promise<boolean> {
    return this.setEffect(INTERNAL_LIGHT_ZONE, "breathing");
  }
  async internalOff(): Promise<boolean> {
    return this.setEffect(INTERNAL_LIGHT_ZONE, "off");
  }

  async externalStatic(r: number, g: number, b: number): Promise<boolean> {
    return this.setEffect(EXTERNAL_LIGHT_ZONE, "static", { r, g, b });
  }
  async externalSpectrum(): Promise<boolean> {
    return this.setEffect(EXTERNAL_LIGHT_ZONE, "spectrum");
  }
  async externalBreathing(): Promise<boolean> {
    return this.setEffect(EXTERNAL_LIGHT_ZONE, "breathing");
  }
  async externalWave(leftToRight = true, rate = 50): Promise<boolean> {
    return this.setEffect(EXTERNAL_LIGHT_ZONE, "wave", {
      waveLeftToRight: leftToRight,
      waveRate: rate,
    });
  }
  async externalOff(): Promise<boolean> {
    return this.setEffect(EXTERNAL_LIGHT_ZONE, "off");
  }
}

function dataViewToBytes(view: DataView): Uint8Array {
  const out = new Uint8Array(view.byteLength);
  for (let i = 0; i < view.byteLength; i++) out[i] = view.getUint8(i);
  return out;
}

function sleep(ms: number): Promise<void> {
  return new Promise((r) => setTimeout(r, ms));
}
