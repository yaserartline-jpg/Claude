#!/usr/bin/env bash
# Rebuild Artline-Company-Profile.pdf from the website (artline-profile.html is the single source).
# Run after every update to the page:  ./make-pdf.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
node "$DIR/print/build-pdf.mjs" "$@"
