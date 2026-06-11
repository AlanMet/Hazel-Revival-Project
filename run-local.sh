#!/usr/bin/env bash
# Visual Hazel Revival UI — serves public/ over HTTPS for Web Bluetooth.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
REQUESTED_PORT="${1:-8765}"
VERSION="$(sed -n 's/export const APP_VERSION = "\(.*\)";/\1/p' "$ROOT/public/js/version.js")"

open_browser() {
  local url="$1"
  if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$url" 2>/dev/null &
  fi
}

is_hazel_server() {
  local port="$1"
  curl -sk --max-time 2 "https://127.0.0.1:${port}/js/version.js" 2>/dev/null | grep -q "APP_VERSION"
}

port_in_use() {
  local port="$1"
  ss -tln 2>/dev/null | grep -q ":${port} " || netstat -tln 2>/dev/null | grep -q ":${port} "
}

echo "Hazel Revival — visual control panel (v${VERSION:-dev})"
echo ""
echo "  Mask photo · tap zones · fan & lighting controls"
echo ""

if is_hazel_server "$REQUESTED_PORT"; then
  URL="https://127.0.0.1:${REQUESTED_PORT}/"
  echo "Server already running — opening ${URL}"
  echo ""
  open_browser "$URL"
  exit 0
fi

PORT="$REQUESTED_PORT"
if port_in_use "$PORT"; then
  echo "Port ${PORT} is in use (not this app). Trying another port…"
  PORT=""
  for candidate in $(seq $((REQUESTED_PORT + 1)) $((REQUESTED_PORT + 20))); do
    if ! port_in_use "$candidate"; then
      PORT="$candidate"
      break
    fi
  done
  if [[ -z "$PORT" ]]; then
    echo "No free port found. Stop the other process, e.g.:"
    echo "  fuser -k ${REQUESTED_PORT}/tcp"
    exit 1
  fi
fi

URL="https://127.0.0.1:${PORT}/"
echo "  1. Pair Razer Zephyr in system Bluetooth settings"
echo "  2. Open in Chromium/Chrome: ${URL}"
echo "  3. Linux: chrome://flags/#enable-experimental-web-platform-features"
echo ""
echo "Starting server on port ${PORT}…"
echo ""

open_browser "$URL"
exec "$ROOT/serve.sh" "$PORT"
