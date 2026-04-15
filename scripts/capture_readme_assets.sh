#!/usr/bin/env bash
# Capture README screenshots (manual driver + optional window id).
# Prerequisites: app running (make run), docs/assets/ exists.
#
# Usage:
#   ./scripts/capture_readme_assets.sh           # macOS: full screen after5s delay
#   ./scripts/capture_readme_assets.sh WINDOW_ID#
# On macOS, WINDOW_ID can be from: osascript -e 'tell app "System Events" to get id of window 1 of process "Chromium"'
# Or use any tool that can screenshot a browser window after you start an analysis.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/docs/assets"
DELAY="${CAPTURE_DELAY:-5}"

mkdir -p "$OUT"

if [[ "$(uname -s)" == "Darwin" ]]; then
  if [[ "${1:-}" != "" ]]; then
    screencapture -l"$1" "$OUT/screenshot-pipeline.png"
  else
    echo "In $DELAY seconds, focus the browser showing the StockSage pipeline UI..."
    sleep "$DELAY"
    screencapture -i "$OUT/screenshot-pipeline.png" || true
  fi
  echo "Saved $OUT/screenshot-pipeline.png"
  echo "For the Financial Health card, scroll to that card and run:"
  echo "  screencapture -i $OUT/screenshot-financial-health.png"
else
  echo "On Linux, use gnome-screenshot, grim, or a browser extension; save to:"
  echo "  $OUT/screenshot-pipeline.png"
  echo "  $OUT/screenshot-financial-health.png"
fi

echo "Optional: record a short GIF with peek, licecap, or ffmpeg and link it from README."
