#!/usr/bin/env bash
# Minimal Android emulator for inspecting com.razer.hazel (Zephyr app).
# Run from repo root: ./tools/scripts/setup-android-emulator.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
APK="$ROOT/legacy/apk/com.razer.hazel.apk"
AVD_NAME="${AVD_NAME:-hazel_re}"
API_LEVEL="${API_LEVEL:-33}"

export ANDROID_HOME="${ANDROID_HOME:-/opt/homebrew/share/android-commandlinetools}"
export ANDROID_SDK_ROOT="$ANDROID_HOME"
if [[ -d /opt/homebrew/opt/openjdk@21/bin ]]; then
  export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home}"
  export PATH="/opt/homebrew/opt/openjdk@21/bin:$PATH"
fi
export PATH="$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$ANDROID_HOME/emulator:$PATH"

die() { echo "error: $*" >&2; exit 1; }
[[ -f "$APK" ]] || die "APK not found: $APK"

if ! command -v java >/dev/null 2>&1; then
  echo "Java required. Install with: brew install openjdk@21"
  exit 1
fi
if ! command -v sdkmanager >/dev/null 2>&1; then
  echo "Android cmdline-tools required. Install with:"
  echo "  brew install openjdk@21"
  echo "  brew install --cask android-commandlinetools"
  exit 1
fi

IMG="system-images;android-${API_LEVEL};google_apis;arm64-v8a"

echo "==> Accepting SDK licenses"
yes | sdkmanager --licenses >/dev/null 2>&1 || true

echo "==> Installing emulator + platform ${API_LEVEL} (arm64, ~1–2 GB download)"
sdkmanager --install "platform-tools" "emulator" "platforms;android-${API_LEVEL}" "$IMG"

if ! avdmanager list avd 2>/dev/null | grep -q "Name: ${AVD_NAME}"; then
  echo "==> Creating AVD ${AVD_NAME}"
  echo "no" | avdmanager create avd -n "$AVD_NAME" -k "$IMG" -d pixel_6
fi

echo ""
echo "Setup done."
echo ""
echo "Start emulator:"
echo "  export ANDROID_HOME=$ANDROID_HOME"
echo "  export PATH=\"\$ANDROID_HOME/emulator:\$ANDROID_HOME/platform-tools:\$PATH\""
echo "  emulator -avd $AVD_NAME &"
echo ""
echo "Install APK (after boot):"
echo "  adb wait-for-device"
echo "  adb install -r \"$APK\""
echo ""
echo "Launch:"
echo "  adb shell monkey -p com.razer.hazel -c android.intent.category.LAUNCHER 1"
