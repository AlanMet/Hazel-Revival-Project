"""Human-readable decode hints for GATT payloads (reverse-engineering aid)."""

from __future__ import annotations

_STATUS: dict[int, str] = {
    0x02: "OK",
    0x03: "ready",
    0x07: "data",
}


def _short_uuid(uuid: str) -> str:
    head = uuid.lower().split("-", 1)[0]
    if head.startswith("0000") and len(head) == 8:
        return head
    return head[:8]


def decode_vendor_frame(data: bytes) -> str:
    if not data:
        return "empty"
    if len(data) < 8:
        return f"short ({len(data)}B) {data.hex(' ')}"
    req = data[0]
    status = data[7]
    st = _STATUS.get(status, f"status=0x{status:02X}")
    parts = [f"req=0x{req:02X}", st]
    if len(data) > 8:
        tail = data[8:]
        if len(tail) <= 4:
            parts.append(f"tail={tail.hex(' ')}")
        else:
            parts.append(f"payload[{len(tail)}B]={tail[:6].hex(' ')}…")
    return " ".join(parts)


def decode_gatt_payload(char_uuid: str, data: bytes) -> str | None:
    short = _short_uuid(char_uuid)
    if short == "00002a19" and len(data) >= 1:
        pct = data[0]
        if pct > 100:
            pct = round(pct * 100 / 255)
        return f"Battery {pct}%"
    if short == "00002a29":
        try:
            text = data.decode("utf-8").strip("\x00")
            if text:
                return f"Text: {text!r}"
        except UnicodeDecodeError:
            pass
    if short == "00002a50" and len(data) >= 7:
        return (
            f"PnP vendor=0x{data[0]:02X}{data[1]:02X} "
            f"product=0x{data[2]:02X}{data[3]:02X}{data[4]:02X}{data[5]:02X} "
            f"ver=0x{data[6]:02X}"
        )
    u = char_uuid.lower()
    if "52401525" in u or "52401526" in u:
        return decode_vendor_frame(data)
    if "52401524" in u and len(data) >= 4:
        return f"vendor write key={data[4:8].hex(' ')}"
    return None
