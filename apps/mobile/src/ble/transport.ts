import { BleClient, BleDevice, numberToUUID, ScanResult } from "@capacitor-community/bluetooth-le";

import {
  BATTERY_CHAR_UUID,
  DEVICE_NAME_PATTERNS,
  RAZER_VENDOR_NOTIFY,
  RAZER_VENDOR_NOTIFY_EXTRA,
  RAZER_VENDOR_SERVICE,
  RAZER_VENDOR_WRITE,
} from "../protocol/constants.js";

export interface ScannedDevice {
  deviceId: string;
  name: string;
}

function matchesName(name: string | undefined | null): boolean {
  if (!name) return false;
  const lower = name.toLowerCase();
  return DEVICE_NAME_PATTERNS.some((p) => lower.includes(p.toLowerCase()));
}

export class BleTransport {
  private deviceId: string | null = null;
  private notifyCallbacks: Map<string, Array<(data: DataView) => void>> = new Map();

  async initialize(): Promise<void> {
    await BleClient.initialize();
  }

  async scan(timeoutMs = 8000): Promise<ScannedDevice[]> {
    const found = new Map<string, ScannedDevice>();

    await BleClient.requestLEScan(
      { services: [RAZER_VENDOR_SERVICE] },
      (result: ScanResult) => {
        const name = result.localName ?? result.device.name ?? "Unknown";
        if (matchesName(name)) {
          found.set(result.device.deviceId, {
            deviceId: result.device.deviceId,
            name,
          });
        }
      },
    );

    await new Promise((r) => setTimeout(r, timeoutMs));
    await BleClient.stopLEScan();
    return [...found.values()];
  }

  async connect(deviceId: string): Promise<void> {
    await BleClient.connect(deviceId, (disconnectedId) => {
      if (disconnectedId === this.deviceId) {
        this.deviceId = null;
      }
    });
    this.deviceId = deviceId;
    await this.subscribeNotifications();
  }

  async disconnect(): Promise<void> {
    if (this.deviceId) {
      await BleClient.disconnect(this.deviceId);
      this.deviceId = null;
    }
  }

  get connected(): boolean {
    return this.deviceId !== null;
  }

  private async subscribeNotifications(): Promise<void> {
    if (!this.deviceId) return;
    const uuids = [RAZER_VENDOR_NOTIFY, RAZER_VENDOR_NOTIFY_EXTRA, BATTERY_CHAR_UUID];
    for (const uuid of uuids) {
      try {
        await BleClient.startNotifications(
          this.deviceId,
          RAZER_VENDOR_SERVICE,
          uuid,
          (value) => {
            const cbs = this.notifyCallbacks.get(uuid.toLowerCase()) ?? [];
            for (const cb of cbs) cb(value);
          },
        );
      } catch {
        // optional char may be missing
      }
    }
  }

  onNotify(uuid: string, cb: (data: DataView) => void): void {
    const key = uuid.toLowerCase();
    const list = this.notifyCallbacks.get(key) ?? [];
    list.push(cb);
    this.notifyCallbacks.set(key, list);
  }

  async write(charUuid: string, data: Uint8Array): Promise<void> {
    if (!this.deviceId) throw new Error("Not connected");
    const view = new DataView(data.buffer, data.byteOffset, data.byteLength);
    await BleClient.write(this.deviceId, RAZER_VENDOR_SERVICE, charUuid, view);
  }

  async readBattery(): Promise<number | null> {
    if (!this.deviceId) return null;
    try {
      const view = await BleClient.read(
        this.deviceId,
        numberToUUID("180f"),
        BATTERY_CHAR_UUID,
      );
      const pct = view.getUint8(0);
      return pct > 100 ? Math.round((pct * 100) / 255) : pct;
    } catch {
      return null;
    }
  }

  async waitForNotify(
    charUuid: string,
    timeoutMs: number,
    collected: Uint8Array[],
  ): Promise<Uint8Array[]> {
    return new Promise((resolve) => {
      const handler = (view: DataView) => {
        const copy = new Uint8Array(view.byteLength);
        for (let i = 0; i < view.byteLength; i++) copy[i] = view.getUint8(i);
        collected.push(copy);
      };
      this.onNotify(charUuid, handler);
      setTimeout(() => resolve(collected), timeoutMs);
    });
  }
}

export async function requestDevice(): Promise<BleDevice | null> {
  try {
    return await BleClient.requestDevice({
      services: [RAZER_VENDOR_SERVICE],
      optionalServices: [RAZER_VENDOR_SERVICE],
    });
  } catch {
    return null;
  }
}

export { RAZER_VENDOR_WRITE, RAZER_VENDOR_NOTIFY, RAZER_VENDOR_NOTIFY_EXTRA };
