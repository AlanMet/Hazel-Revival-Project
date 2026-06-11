#!/usr/bin/env python3
"""Serve public/ on all interfaces over HTTP."""

from __future__ import annotations

import functools
import http.server
import socket
import socketserver
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8765


class ReusableHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True


def lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def main() -> None:
    if not PUBLIC.is_dir():
        raise SystemExit(f"Missing {PUBLIC}")

    ip = lan_ip()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PUBLIC))

    httpd = ReusableHTTPServer(("0.0.0.0", PORT), handler)
    httpd.allow_reuse_address = True

    print(f"Serving {PUBLIC} (HTTP, all interfaces)")
    print(f"  This machine:  http://127.0.0.1:{PORT}/")
    print(f"  Network:       http://{ip}:{PORT}/")
    print("Use Chromium. Open http://127.0.0.1 for Web Bluetooth on this machine.")
    print("Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
