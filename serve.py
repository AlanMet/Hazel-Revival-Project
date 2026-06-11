#!/usr/bin/env python3
"""Serve public/ on all interfaces with HTTPS (required for Web Bluetooth over LAN)."""

from __future__ import annotations

import functools
import http.server
import socket
import socketserver
import ssl
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
CERT_DIR = ROOT / ".serve-certs"
CERT = CERT_DIR / "cert.pem"
KEY = CERT_DIR / "key.pem"
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


def ensure_cert() -> None:
    if CERT.exists() and KEY.exists():
        return
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(KEY),
            "-out",
            str(CERT),
            "-days",
            "365",
            "-nodes",
            "-subj",
            "/CN=localhost",
        ],
        check=True,
    )


def main() -> None:
    if not PUBLIC.is_dir():
        raise SystemExit(f"Missing {PUBLIC}")

    ensure_cert()
    ip = lan_ip()

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PUBLIC))

    httpd = ReusableHTTPServer(("0.0.0.0", PORT), handler)
    httpd.allow_reuse_address = True
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(CERT, KEY)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)

    print(f"Serving {PUBLIC} (HTTPS, all interfaces)")
    print(f"  This machine:  https://127.0.0.1:{PORT}/")
    print(f"  Network:       https://{ip}:{PORT}/")
    print("Use Chromium. Accept the self-signed certificate warning once.")
    print("Press Ctrl+C to stop.")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
