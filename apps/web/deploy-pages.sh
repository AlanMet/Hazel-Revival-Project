#!/usr/bin/env bash
# Publish public/ to GitHub Pages (force-push site-only branch).
# Set GITHUB_PAGES_REPO before running, e.g.:
#   GITHUB_PAGES_REPO=https://github.com/you/hazel-revive.git ./deploy-pages.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUILD="${TMPDIR:-/tmp}/hazel-revive-web"
VERSION="$(sed -n 's/export const APP_VERSION = "\(.*\)";/\1/p' "$ROOT/public/js/version.js")"
REPO="${GITHUB_PAGES_REPO:?Set GITHUB_PAGES_REPO to the GitHub repo URL}"

rm -rf "$BUILD"
mkdir -p "$BUILD"
cp -r "$ROOT/public/assets" "$ROOT/public/css" "$ROOT/public/js" "$ROOT/public/index.html" "$BUILD/"
printf '%s\n\nDeploy with ./apps/web/deploy-pages.sh\n' "# Hazel Revive (web)" > "$BUILD/README.md"

cd "$BUILD"
git init -q
git checkout -b gh-pages
git add -A
git commit -q -m "Deploy Hazel Revive web v${VERSION}."
git remote add origin "$REPO" 2>/dev/null || git remote set-url origin "$REPO"
git push -u origin gh-pages --force

echo "Deployed v${VERSION} from public/"
