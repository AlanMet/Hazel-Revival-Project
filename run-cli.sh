#!/usr/bin/env bash
# Native Zephyr CLI (bleak) — uses project .venv, no system pip needed.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if [[ ! -x "$VENV/bin/zephyr-re" ]]; then
  echo "First-time setup — creating .venv and installing zephyr-re…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -e "$ROOT"
fi

exec "$VENV/bin/zephyr-re" "$@"
