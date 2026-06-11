/** Parse vendor notify frames for command ACK (byte 7 === 0x02). */

import { STATUS_SUCCESS } from "./constants.js";

export function parseAck(frames) {
  const ack = frames.some(
    (frame) => frame.byteLength >= 8 && frame[7] === STATUS_SUCCESS,
  );
  return { ok: ack, frames };
}
