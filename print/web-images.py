#!/usr/bin/env python3
"""Make resized copies of every photo the brochure uses (print/web-img/), for the lighter web PDF."""
import sys
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent.parent
out = root / "print" / "web-img"
for rel in sys.argv[1:]:
    src = root / rel; dst = out / rel
    if not src.exists() or src.suffix.lower() not in (".jpg", ".jpeg", ".png") or "logo" in src.name or "clients" in rel or "brands" in rel or "partners" in rel:
        continue
    if dst.exists() and dst.stat().st_mtime > src.stat().st_mtime: continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    im = Image.open(src).convert("RGB"); im.thumbnail((1600, 1600), Image.LANCZOS)
    im.save(dst.with_suffix(".jpg") if dst.suffix == ".png" else dst, quality=82, optimize=True, progressive=True)
