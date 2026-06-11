#!/usr/bin/env bash
# Publish public/ to GitHub Pages (force-push site-only main).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="${TMPDIR:-/tmp}/hazel-public-site"
VERSION="$(sed -n 's/export const APP_VERSION = "\(.*\)";/\1/p' "$ROOT/public/js/version.js")"

rm -rf "$BUILD"
mkdir -p "$BUILD"
cp -r "$ROOT/public/assets" "$ROOT/public/css" "$ROOT/public/js" "$ROOT/public/index.html" "$BUILD/"
printf '%s\n\n%s\n' "# Hazel Revival" "https://alanmet.github.io/Hazel-Revival-Project/" > "$BUILD/README.md"

cd "$BUILD"
git init -q
git checkout -b main
git add -A
git commit -q -m "$(cat <<EOF
Deploy Hazel Revival v${VERSION}.

Simplified Web Bluetooth gate and macOS unsupported notice.
EOF
)"
git remote add origin https://github.com/AlanMet/Hazel-Revival-Project.git 2>/dev/null || true
git push -u origin main --force

echo "Deployed v${VERSION} → https://alanmet.github.io/Hazel-Revival-Project/"
