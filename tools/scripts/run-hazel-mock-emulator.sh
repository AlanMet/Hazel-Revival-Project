#!/usr/bin/env bash
# Launch Hazel APK in the emulator with a mock "connected" Zephyr (no BLE).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FRIDA_SCRIPT="$ROOT/tools/frida/hazel-mock-connected.js"
APK="$ROOT/legacy/apk/com.razer.hazel.apk"
AVD_NAME="${AVD_NAME:-hazel_re}"

export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"
if [[ -d /opt/homebrew/opt/openjdk@21/bin ]]; then
  export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
fi

die() { echo "error: $*" >&2; exit 1; }
[[ -f "$FRIDA_SCRIPT" ]] || die "Missing $FRIDA_SCRIPT"

if ! adb devices | grep -q 'emulator-'; then
  echo "No emulator running. Start with:"
  echo "  emulator -avd $AVD_NAME &"
  exit 1
fi

if ! command -v frida >/dev/null 2>&1; then
  echo "Install Frida CLI: pip install frida-tools"
  exit 1
fi

FRIDA_VER="$(frida --version)"
echo "Frida client $FRIDA_VER"

# Install frida-server on emulator if missing
if ! adb shell "test -f /data/local/tmp/frida-server && echo ok" 2>/dev/null | grep -q ok; then
  echo "==> Installing frida-server ($FRIDA_VER) on emulator"
  FRIDA_SERVER_XZ="$(mktemp /tmp/frida-server-XXXXXX.xz)"
  curl -fsSL "https://github.com/frida/frida/releases/download/${FRIDA_VER}/frida-server-${FRIDA_VER}-android-arm64.xz" -o "$FRIDA_SERVER_XZ"
  xz -d -f "$FRIDA_SERVER_XZ"
  FRIDA_SERVER_BIN="${FRIDA_SERVER_XZ%.xz}"
  adb root >/dev/null 2>&1 || true
  adb push "$FRIDA_SERVER_BIN" /data/local/tmp/frida-server
  adb shell chmod 755 /data/local/tmp/frida-server
  adb shell '/data/local/tmp/frida-server -D &' 
  sleep 2
  rm -f "$FRIDA_SERVER_BIN"
fi

adb wait-for-device
adb install -r "$APK" >/dev/null 2>&1 || true

echo "==> Spawning com.razer.hazel with mock connected device"
echo "    Dashboard should show Internal/External lighting, Fan, Buy Filters."
echo "    Effect writes are stubbed — UI exploration only."
exec frida -U -f com.razer.hazel -l "$FRIDA_SCRIPT"
