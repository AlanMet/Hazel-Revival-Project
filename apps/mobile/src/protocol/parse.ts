import type { FanSpeed } from "./constants.js";

const FAN_MAP: Record<number, FanSpeed> = { 0: "off", 1: "low", 2: "high" };
const HAZEL_EFFECT: Record<number, string> = {
  0: "off",
  1: "static",
  2: "breathing",
  3: "spectrum",
  4: "wave",
};

export interface DeviceState {
  batteryPercent: number | null;
  fanSpeed: FanSpeed;
  fanSpeedSource: string;
  externalEffect: string | null;
  internalEffect: string | null;
  firmwareVersion: string | null;
  isCharging: boolean | null;
}

export function bytesToHex(data: Uint8Array): string {
  return Array.from(data)
    .map((b) => b.toString(16).padStart(2, "0").toUpperCase())
    .join(" ");
}

export function writeAck(frames: Uint8Array[]): boolean {
  return frames.some((f) => f.length >= 8 && f[7] === 0x02);
}

export function parseBattery(data: Uint8Array): number | null {
  if (!data.length) return null;
  const pct = data[0];
  return pct > 100 ? Math.round((pct * 100) / 255) : pct;
}

export function parseFanRead(frames: Uint8Array[]): FanSpeed | null {
  for (const frame of frames) {
    if (frame.length >= 3 && FAN_MAP[frame[2]]) {
      return FAN_MAP[frame[2]];
    }
  }
  return null;
}

export function parseExtraFan(frame: Uint8Array): FanSpeed | null {
  if (frame.length >= 3 && frame[0] === 0x05 && frame[1] === 0x39) {
    return FAN_MAP[frame[2]] ?? null;
  }
  return null;
}

export function parseEffect(frames: Uint8Array[]): string | null {
  for (const frame of frames) {
    if (frame.length >= 8 && frame[7] === 0x02) {
      const tail = frame.slice(8);
      if (tail.length && HAZEL_EFFECT[tail[0]]) {
        return HAZEL_EFFECT[tail[0]];
      }
    }
    if (frame.length && HAZEL_EFFECT[frame[0]]) {
      return HAZEL_EFFECT[frame[0]];
    }
  }
  return null;
}

export function parseFirmware(frames: Uint8Array[]): string | null {
  for (const frame of frames) {
    if (frame.length >= 8 && frame[7] === 0x02) {
      const tail = frame.slice(8);
      if (tail.length >= 4) {
        return formatFw(tail.slice(0, 4));
      }
    }
    if (frame.length >= 4 && frame[0] < 0x10) {
      return formatFw(frame.slice(0, 4));
    }
  }
  return null;
}

function formatFw(chunk: Uint8Array): string {
  return `${chunk[0].toString().padStart(2, "0")}.${chunk[1]
    .toString()
    .padStart(2, "0")}.${chunk[2].toString().padStart(2, "0")}.${chunk[3]
    .toString()
    .padStart(2, "0")}`;
}

export function parseCharging(frames: Uint8Array[]): boolean | null {
  for (const frame of frames) {
    if (frame.length >= 8 && frame[7] === 0x02) {
      const tail = frame.slice(8);
      if (tail.length) return tail[0] !== 0;
    }
  }
  return null;
}
