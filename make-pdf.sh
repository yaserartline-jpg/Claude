#!/usr/bin/env bash
# Rebuild the company profile PDFs and the standalone HTML from the website (artline-profile.html is the single source).
#   Artline-Company-Profile.pdf      full-quality print master
#   Artline-Company-Profile-web.pdf  lighter copy served by the website's download button
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
node "$DIR/print/build-pdf.mjs" "$@"
node "$DIR/print/build-pdf.mjs" --web
python3 "$DIR/print/standalone.py"   # Artline-Company-Profile.html: self-contained copy for sharing
