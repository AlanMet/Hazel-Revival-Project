"""Hex parsing and formatting helpers for raw GATT probes."""

from __future__ import annotations


def parse_hex(s: str) -> bytes:
    """Parse space-separated or continuous hex string into bytes."""
    cleaned = s.replace(",", " ").replace("0x", "").replace("0X", "")
    parts = cleaned.split()
    if len(parts) == 1 and len(parts[0]) % 2 == 0:
        return bytes.fromhex(parts[0])
    return bytes(int(p, 16) for p in parts if p)


def format_hex(data: bytes, sep: str = " ") -> str:
    """Format bytes as uppercase hex."""
    return sep.join(f"{b:02X}" for b in data)


def format_hex_lines(data: bytes, width: int = 16) -> str:
    """Format bytes in hex dump style."""
    lines: list[str] = []
    for i in range(0, len(data), width):
        chunk = data[i : i + width]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        lines.append(f"{i:04X}  {hex_part}")
    return "\n".join(lines)
