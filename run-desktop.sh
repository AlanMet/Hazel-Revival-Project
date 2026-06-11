#!/usr/bin/env bash
# Hazel Revival desktop app — native GUI (CustomTkinter + bleak).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/.venv"

if ! python3 -c "import tkinter" 2>/dev/null; then
  echo "Tk is required for the desktop UI but is not installed."
  echo ""
  echo "  Arch:   sudo pacman -S tk"
  echo "  Debian: sudo apt install python3-tk"
  echo "  Fedora: sudo dnf install python3-tkinter"
  echo ""
  exit 1
fi

if [[ ! -x "$VENV/bin/hazel-revival" ]]; then
  echo "First-time setup — creating .venv and installing desktop app…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -e "$ROOT[desktop]"
fi

exec "$VENV/bin/hazel-revival" "$@"
