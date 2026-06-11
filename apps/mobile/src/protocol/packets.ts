import {
  EXTERNAL_LIGHT_ZONE,
  INTERNAL_LIGHT_ZONE,
  WAVE_RATE_FACTORY,
  type FanSpeed,
  FAN_LEVEL,
} from "./constants.js";

export type EffectName = "off" | "static" | "breathing" | "spectrum" | "wave";

const EFFECT_TYPE: Record<EffectName, number> = {
  off: 0,
  static: 1,
  breathing: 2,
  spectrum: 3,
  wave: 4,
};

export function buildReadHeader(reqId: number, key: number[]): Uint8Array {
  return new Uint8Array([reqId & 0xff, 0x00, 0x00, 0x00, ...key]);
}

function effectSetHeader(
  reqId: number,
  payload: Uint8Array,
  zone: number,
  subId = 0,
): Uint8Array {
  const plen = payload.length;
  return new Uint8Array([
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
  effectType: number,
  param1 = 0,
  param2 = 0,
  color1?: [number, number, number],
  color2?: [number, number, number],
): Uint8Array {
  const body: number[] = [effectType & 0xff, param1 & 0xff, param2 & 0xff];
  if (!color1 && !color2) {
    body.push(0);
  } else if (color1 && !color2) {
    body.push(1, ...color1.map((c) => c & 0xff));
  } else {
    body.push(2);
    if (color1) body.push(...color1.map((c) => c & 0xff));
    if (color2) body.push(...color2.map((c) => c & 0xff));
  }
  return new Uint8Array(body);
}

export interface EffectOptions {
  r?: number;
  g?: number;
  b?: number;
  waveLeftToRight?: boolean;
  waveRate?: number;
}

export function effectPackets(
  reqId: number,
  effect: EffectName,
  zone: number,
  opts: EffectOptions = {},
): [Uint8Array, Uint8Array] {
  const name = effect.toLowerCase() as EffectName;
  const effectType = EFFECT_TYPE[name];
  if (effectType === undefined) {
    throw new Error(`Unknown effect: ${effect}`);
  }

  let payload: Uint8Array;
  if (effectType === 0) {
    payload = new Uint8Array([0]);
  } else if (effectType === 1) {
    payload = bleEffectConfiguration(1, 0, 0, [
      opts.r ?? 0,
      opts.g ?? 0,
      opts.b ?? 0,
    ]);
  } else if (effectType === 2) {
    const c1 =
      opts.r || opts.g || opts.b
        ? ([opts.r ?? 0, opts.g ?? 0, opts.b ?? 0] as [number, number, number])
        : undefined;
    payload = bleEffectConfiguration(2, 0, 0, c1);
  } else if (effectType === 3) {
    payload = bleEffectConfiguration(3, 0, 0);
  } else {
    const direction = opts.waveLeftToRight !== false ? 1 : 2;
    payload = bleEffectConfiguration(
      4,
      direction,
      (opts.waveRate ?? WAVE_RATE_FACTORY) & 0xff,
    );
  }
  return [effectSetHeader(reqId, payload, zone), payload];
}

export function fanSpeedPackets(
  reqId: number,
  speed: FanSpeed,
): [Uint8Array, Uint8Array] {
  const level = FAN_LEVEL[speed];
  const header = new Uint8Array([
    reqId & 0xff, 0x06, 0x00, 0x00, 0x11, 0x01, 0x01, 0x00,
  ]);
  const payload = new Uint8Array([
    0x01, 0x00, level & 0xff, 0x00, level & 0xff, 0x00,
  ]);
  return [header, payload];
}

export const ZONE_BRIGHTNESS_KEY = (zone: number) => [0x10, 0x85, 0x00, zone];
export const ZONE_EFFECT_KEY = (zone: number) => [0x10, 0x83, 0x00, zone];
export const KEY_READ_FAN = [0x11, 0x81, 0x01, 0x00];
export const KEY_READ_FIRMWARE = [0x00, 0x81, 0x00, 0x00];
export const KEY_READ_CHARGING = [0x05, 0x85, 0x00, 0x00];

export { EXTERNAL_LIGHT_ZONE, INTERNAL_LIGHT_ZONE };
