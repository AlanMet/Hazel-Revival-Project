/** Web Bluetooth transport — GATT only, no Razer packet logic. */

import {
  DEVICE_NAME_PREFIXES,
  formatDisplayDeviceName,
  GAP_DEVICE_NAME_CHAR,
  GAP_SERVICE,
  isZephyrDeviceName,
  NOTIFY_TIMEOUT_MS,
  RAZER_VENDOR_NOTIFY,
  RAZER_VENDOR_SERVICE,
  RAZER_VENDOR_WRITE,
} from "./protocol/constants.js";
import { connectLog } from "./connect-log.js";
import { getWebBluetoothStatus } from "./browser.js";

const GATT_CONNECT_TIMEOUT_MS = 15000;

function buildDeviceFilters() {
  // Name-only filters — a service filter makes Chrome show the UUID hex in the picker.
  return DEVICE_NAME_PREFIXES.map((prefix) => ({ namePrefix: prefix }));
}

async function readGapDeviceName(server) {
  try {
    const service = await server.getPrimaryService(GAP_SERVICE);
    const char = await service.getCharacteristic(GAP_DEVICE_NAME_CHAR);
    const value = await char.readValue();
    const name = new TextDecoder().decode(value).trim();
    return name || null;
  } catch {
    return null;
  }
}

async function resolveZephyrName(server, advertisedName) {
  if (isZephyrDeviceName(advertisedName)) {
    return formatDisplayDeviceName(advertisedName);
  }
  const gapName = await readGapDeviceName(server);
  if (isZephyrDeviceName(gapName)) {
    return formatDisplayDeviceName(gapName);
  }
  return null;
}

function withTimeout(promise, ms, message) {
  return Promise.race([
    promise,
    new Promise((_, reject) => {
      setTimeout(() => reject(new Error(message)), ms);
    }),
  ]);
}

export function formatBleError(err, deviceName) {
  const name = err?.name ?? "";
  const msg = err?.message ?? String(err);

  if (/unsupported device/i.test(msg)) {
    if (isZephyrDeviceName(deviceName)) {
      return (
        "Could not link to your Zephyr. Disconnect it in System Settings → Bluetooth, " +
        "wake the mask (LEDs on), then try Connect again."
      );
    }
    return 'Pick a device whose name includes "Zephyr" (e.g. "Razer Zephyr - paired").';
  }
  if (name === "NotFoundError" || /user cancelled/i.test(msg)) {
    return "No device selected.";
  }
  if (/timed out/i.test(msg)) {
    return (
      "Connection timed out. Disconnect the mask in Bluetooth settings, wake it, and try again."
    );
  }
  if (name === "NetworkError" || /gatt/i.test(msg)) {
    return (
      "Could not connect over Bluetooth. Stay within a metre and disconnect the mask " +
      "from macOS Bluetooth settings if it shows as connected."
    );
  }
  if (name === "SecurityError") {
    return "Bluetooth permission blocked — allow Chrome in System Settings → Privacy & Security → Bluetooth.";
  }
  return msg;
}

export class BluetoothTransport {
  #device = null;
  #server = null;
  #displayName = null;
  #notifyHandlers = new Map();
  #lastDebug = [];

  get lastDebug() {
    return this.#lastDebug;
  }

  get isConnected() {
    return Boolean(this.#device?.gatt?.connected);
  }

  get deviceName() {
    return this.#displayName ?? formatDisplayDeviceName(this.#device?.name);
  }

  #debug(step, detail = {}) {
    const entry = { step, ...detail, at: new Date().toISOString() };
    this.#lastDebug.push(entry);
    const parts = [`${step}`];
    for (const [key, value] of Object.entries(detail)) {
      if (value != null && typeof value !== "object") parts.push(`${key}=${JSON.stringify(value)}`);
    }
    connectLog(`ble: ${parts.join(" ")}`);
  }

  async connect({ acceptAll = false } = {}) {
    this.#lastDebug = [];
    const t0 = performance.now();
    const elapsed = () => `${Math.round(performance.now() - t0)}ms`;
    const useAcceptAll = acceptAll;

    const status = getWebBluetoothStatus();
    if (!status.ok) {
      this.#debug("precheck.fail", { elapsed: elapsed(), reason: status.message });
      throw new Error(status.hint ? `${status.message} ${status.hint}` : status.message);
    }

    this.#debug("connect.start", {
      elapsed: elapsed(),
      acceptAll: useAcceptAll,
      filters: useAcceptAll ? null : buildDeviceFilters(),
      optionalServices: [RAZER_VENDOR_SERVICE],
    });

    await this.disconnect();

    let pickedName = null;
    let pickedId = null;
    let phase = "requestDevice";

    try {
      this.#device = useAcceptAll
        ? await navigator.bluetooth.requestDevice({
            acceptAllDevices: true,
            optionalServices: [RAZER_VENDOR_SERVICE],
          })
        : await navigator.bluetooth.requestDevice({
            filters: buildDeviceFilters(),
            optionalServices: [RAZER_VENDOR_SERVICE],
          });

      pickedName = this.#device.name ?? null;
      pickedId = this.#device.id ?? null;
      this.#debug("requestDevice.ok", {
        elapsed: elapsed(),
        name: pickedName,
        id: pickedId,
        zephyrMatch: isZephyrDeviceName(pickedName),
      });

      this.#device.addEventListener("gattserverdisconnected", () => {
        this.#server = null;
        this.#notifyHandlers.clear();
        this.#debug("gatt.disconnected", { elapsed: elapsed() });
      });

      phase = "gatt.connect";
      this.#server = await withTimeout(
        this.#device.gatt.connect(),
        GATT_CONNECT_TIMEOUT_MS,
        "Connection timed out",
      );
      this.#debug("gatt.connect.ok", {
        elapsed: elapsed(),
        connected: this.#device.gatt?.connected ?? false,
      });

      phase = "getPrimaryService";
      await this.#server.getPrimaryService(RAZER_VENDOR_SERVICE);
      this.#debug("getPrimaryService.ok", {
        elapsed: elapsed(),
        service: RAZER_VENDOR_SERVICE,
      });

      phase = "resolveName";
      const resolvedName = await resolveZephyrName(this.#server, pickedName);
      if (!resolvedName) {
        throw new Error(
          `Wrong device${pickedName ? `: ${pickedName}` : ""}. Choose one whose name includes "Zephyr".`,
        );
      }
      this.#displayName = resolvedName;
      this.#debug("resolveName.ok", {
        elapsed: elapsed(),
        advertisedName: pickedName,
        displayName: resolvedName,
      });

      return resolvedName;
    } catch (err) {
      this.#debug("connect.fail", {
        elapsed: elapsed(),
        phase,
        deviceName: pickedName,
        deviceId: pickedId,
        errorName: err?.name ?? null,
        errorMessage: err?.message ?? String(err),
        gattConnected: this.#device?.gatt?.connected ?? false,
      });
      await this.disconnect();
      throw new Error(formatBleError(err, pickedName));
    }
  }

  async disconnect() {
    if (this.#device?.gatt?.connected) {
      this.#device.gatt.disconnect();
    }
    this.#device = null;
    this.#server = null;
    this.#displayName = null;
    this.#notifyHandlers.clear();
  }

  async #getCharacteristic(serviceUuid, charUuid) {
    if (!this.#server) {
      throw new Error("Not connected.");
    }
    const service = await this.#server.getPrimaryService(serviceUuid);
    return service.getCharacteristic(charUuid);
  }

  async write(serviceUuid, charUuid, data) {
    const char = await this.#getCharacteristic(serviceUuid, charUuid);
    await char.writeValueWithResponse(data);
  }

  async startNotifications(charUuid, onFrame) {
    const char = await this.#getCharacteristic(RAZER_VENDOR_SERVICE, charUuid);
    this.#notifyHandlers.set(charUuid, onFrame);
    await char.startNotifications();
    char.addEventListener("characteristicvaluechanged", (event) => {
      const value = event.target.value;
      onFrame(new Uint8Array(value.buffer, value.byteOffset, value.byteLength));
    });
  }

  async stopNotifications(charUuid) {
    const char = await this.#getCharacteristic(RAZER_VENDOR_SERVICE, charUuid);
    await char.stopNotifications();
    this.#notifyHandlers.delete(charUuid);
  }

  /** Write one or more chunks to the vendor char; collect notify frames until timeout. */
  async vendorWrite(chunks, timeoutMs = NOTIFY_TIMEOUT_MS) {
    const frames = [];
    const onFrame = (data) => frames.push(data);

    await this.startNotifications(RAZER_VENDOR_NOTIFY, onFrame);
    try {
      for (const chunk of chunks) {
        await this.write(RAZER_VENDOR_SERVICE, RAZER_VENDOR_WRITE, chunk);
      }
      await this.#waitForFrames(frames, timeoutMs);
      return frames;
    } finally {
      await this.stopNotifications(RAZER_VENDOR_NOTIFY).catch(() => {});
    }
  }

  #waitForFrames(frames, timeoutMs) {
    if (frames.length > 0) {
      return Promise.resolve();
    }
    return new Promise((resolve) => setTimeout(resolve, timeoutMs));
  }
}
