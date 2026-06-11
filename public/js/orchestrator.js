/** Feature commands — builds protocol bytes and calls Bluetooth transport. */

import {
  EXTERNAL_LIGHT_ZONE,
  INTERNAL_LIGHT_ZONE,
  REQUEST_ID_START,
} from "./protocol/constants.js";
import { parseAck } from "./protocol/exchange.js";
import { effectPackets, fanSpeedPackets } from "./protocol/packets.js";

export class ZephyrOrchestrator {
  #bt;
  #reqId = REQUEST_ID_START;

  constructor(bluetooth) {
    this.#bt = bluetooth;
  }

  get isConnected() {
    return this.#bt.isConnected;
  }

  get deviceName() {
    return this.#bt.deviceName;
  }

  get lastDebug() {
    return this.#bt.lastDebug;
  }

  async connect(options) {
    try {
      const name = await this.#bt.connect(options);
      return { ok: true, message: `Connected to ${name}`, debug: this.#bt.lastDebug };
    } catch (err) {
      return {
        ok: false,
        message: err instanceof Error ? err.message : String(err),
        debug: this.#bt.lastDebug,
      };
    }
  }

  async disconnect() {
    await this.#bt.disconnect();
    return { ok: true, message: "Disconnected" };
  }

  #nextReqId() {
    const id = this.#reqId;
    this.#reqId = (this.#reqId + 1) & 0xff;
    return id;
  }

  async #sendPair(label, header, payload) {
    if (!this.isConnected) {
      return { ok: false, message: "Not connected" };
    }
    const frames = await this.#bt.vendorWrite([header, payload]);
    const { ok } = parseAck(frames);
    return {
      ok,
      message: ok ? label : `${label} — no device ack`,
    };
  }

  async #sendEffect(zone, effect, label, opts = {}) {
    try {
      const [header, payload] = effectPackets(this.#nextReqId(), effect, zone, opts);
      return this.#sendPair(label, header, payload);
    } catch (err) {
      return {
        ok: false,
        message: err instanceof Error ? err.message : String(err),
      };
    }
  }

  async #sendFan(speed, label) {
    const [header, payload] = fanSpeedPackets(this.#nextReqId(), speed);
    return this.#sendPair(label, header, payload);
  }

  fanLow() {
    return this.#sendFan("low", "Fan low");
  }

  fanHigh() {
    return this.#sendFan("high", "Fan high");
  }

  fanOff() {
    return this.#sendFan("off", "Fan off");
  }

  internalStatic(r = 255, g = 255, b = 255) {
    return this.#sendEffect(
      INTERNAL_LIGHT_ZONE,
      "static",
      `Internal static`,
      { r, g, b },
    );
  }

  internalSpectrum() {
    return this.#sendEffect(INTERNAL_LIGHT_ZONE, "spectrum", "Internal spectrum");
  }

  internalBreathing() {
    return this.#sendEffect(INTERNAL_LIGHT_ZONE, "breathing", "Internal breathing");
  }

  internalOff() {
    return this.#sendEffect(INTERNAL_LIGHT_ZONE, "off", "Internal off");
  }

  externalStatic(r = 255, g = 255, b = 255) {
    return this.#sendEffect(
      EXTERNAL_LIGHT_ZONE,
      "static",
      `External static`,
      { r, g, b },
    );
  }

  externalSpectrum() {
    return this.#sendEffect(EXTERNAL_LIGHT_ZONE, "spectrum", "External spectrum");
  }

  externalBreathing() {
    return this.#sendEffect(EXTERNAL_LIGHT_ZONE, "breathing", "External breathing");
  }

  externalWave(waveRate = 90, waveLeftToRight = true) {
    return this.#sendEffect(EXTERNAL_LIGHT_ZONE, "wave", "External wave", {
      waveRate,
      waveLeftToRight,
    });
  }

  externalOff() {
    return this.#sendEffect(EXTERNAL_LIGHT_ZONE, "off", "External off");
  }
}
