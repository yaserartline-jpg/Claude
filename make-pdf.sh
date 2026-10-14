#!/usr/bin/env bash
# Rebuild Artline-Company-Profile.pdf from artline-profile.html (the single source).
# Run after every update to the page:  ./make-pdf.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CHROME="${CHROME:-$(command -v chromium || command -v google-chrome || command -v chrome || echo /opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell)}"
TMP="$DIR/.print-build.html"
# The page is published as a fragment; wrap it in a full document for printing.
{ echo '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'; cat "$DIR/artline-profile.html"; echo '</html>'; } > "$TMP"
"$CHROME" --headless --no-sandbox --disable-gpu --run-all-compositor-stages-before-draw \
  --virtual-time-budget=20000 --no-pdf-header-footer \
  --print-to-pdf="$DIR/Artline-Company-Profile.pdf" "file://$TMP?pdf" 2>/dev/null
rm -f "$TMP"
echo "Built $DIR/Artline-Company-Profile.pdf"
