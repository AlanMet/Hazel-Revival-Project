#!/usr/bin/env bash
# HTTPS on 0.0.0.0 — Web Bluetooth works on LAN (unlike plain http://192.168.x.x)
set -euo pipefail
PORT="${1:-8765}"
exec python3 "$(dirname "$0")/serve.py" "$PORT"
