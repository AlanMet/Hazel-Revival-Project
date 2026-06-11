/** Hazel APK packet builders — ported from reverse-engineering reference. */

import {
  EXTERNAL_LIGHT_ZONE,
  INTERNAL_LIGHT_ZONE,
} from "./constants.js";

export const FAN_LEVEL = { off: 0, low: 1, high: 2 };

export const EFFECT_TYPE = {
  off: 0,
  static: 1,
  breathing: 2,
  spectrum: 3,
  wave: 4,
};

export const WAVE_RATE_FACTORY = 90;
/** Firmware wave byte: lower = faster rotation, higher = slower. */
export const WAVE_RATE_FAST = 15;
export const WAVE_RATE_MEDIUM = 50;
export const WAVE_RATE_SLOW = 100;

export const WAVE_SPEED_PRESETS = {
  slow: WAVE_RATE_SLOW,
  medium: WAVE_RATE_MEDIUM,
  fast: WAVE_RATE_FAST,
  factory: WAVE_RATE_FACTORY,
};

function effectSetHeader(reqId, payload, { subId = 0, zone }) {
  const plen = payload.length;
  return Uint8Array.from([
    reqId & 0xff,
    plen & 0xff,
    (plen >> 8) & 0xff,
    (plen >> 16) & 0xff,
    0x10,
    0x03,
    subId & 0xff,
    zone & 0xff,
  ]);
}

function bleEffectConfiguration(
  effectType,
  param1 = 0,
  param2 = 0,
  { color1 = null, color2 = null } = {},
) {
  const body = [effectType & 0xff, param1 & 0xff, param2 & 0xff];
  if (!color1 && !color2) {
    body.push(0);
  } else if (color1 && !color2) {
    body.push(1, ...color1.map((c) => c & 0xff));
  } else {
    body.push(2);
    if (color1) body.push(...color1.map((c) => c & 0xff));
    if (color2) body.push(...color2.map((c) => c & 0xff));
  }
  return Uint8Array.from(body);
}

export function effectOffPackets(reqId, zone, { subId = 0 } = {}) {
  const payload = Uint8Array.from([0x00]);
  return [effectSetHeader(reqId, payload, { subId, zone }), payload];
}

export function effectPackets(
  reqId,
  effect,
  zone,
  {
    subId = 0,
    r = 0,
    g = 0,
    b = 0,
    r2 = null,
    g2 = null,
    b2 = null,
    waveLeftToRight = true,
    waveRate = WAVE_RATE_FACTORY,
  } = {},
) {
  const name = effect.toLowerCase();
  const effectType = EFFECT_TYPE[name];
  if (effectType === undefined) {
    throw new Error(`Unknown effect: ${effect}`);
  }

  if (effectType === 0) {
    return effectOffPackets(reqId, zone, { subId });
  }

  let payload;
  if (effectType === 1) {
    payload = bleEffectConfiguration(1, 0, 0, {
      color1: [r & 0xff, g & 0xff, b & 0xff],
    });
  } else if (effectType === 2) {
    const c1 = r || g || b ? [r & 0xff, g & 0xff, b & 0xff] : null;
    const c2 =
      r2 !== null && g2 !== null && b2 !== null
        ? [r2 & 0xff, g2 & 0xff, b2 & 0xff]
        : null;
    payload = bleEffectConfiguration(2, 0, 0, { color1: c1, color2: c2 });
  } else if (effectType === 3) {
    payload = bleEffectConfiguration(3, 0, 0);
  } else if (effectType === 4) {
    const direction = waveLeftToRight ? 1 : 2;
    payload = bleEffectConfiguration(4, direction, waveRate & 0xff);
  } else {
    throw new Error(`Unsupported effect type: ${effectType}`);
  }

  return [effectSetHeader(reqId, payload, { subId, zone }), payload];
}

export function fanSpeedPackets(reqId, speed) {
  const level = FAN_LEVEL[speed];
  const header = Uint8Array.from([
    reqId & 0xff, 0x06, 0x00, 0x00, 0x11, 0x01, 0x01, 0x00,
  ]);
  const payload = Uint8Array.from([
    0x01, 0x00, level & 0xff, 0x00, level & 0xff, 0x00,
  ]);
  return [header, payload];
}
