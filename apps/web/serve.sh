#!/usr/bin/env bash
# HTTP on 0.0.0.0 — use http://127.0.0.1 for Web Bluetooth on this machine
set -euo pipefail
PORT="${1:-8765}"
exec python3 "$(dirname "$0")/serve.py" "$PORT"
