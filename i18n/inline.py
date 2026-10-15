#!/usr/bin/env python3
"""Copy i18n/ar.json into artline-profile.html (between the AR-DATA markers). Run after editing translations."""
import json, re
from pathlib import Path
root = Path(__file__).resolve().parent.parent
page = root / "artline-profile.html"
data = json.dumps(json.loads((root / "i18n" / "ar.json").read_text()), ensure_ascii=False, separators=(",", ":"))
t = page.read_text()
t, n = re.subn(r"/\*AR-DATA\*/.*?/\*END-AR-DATA\*/", lambda m: f"/*AR-DATA*/{data}/*END-AR-DATA*/", t, flags=re.S)
assert n == 1, "AR-DATA markers not found"
page.write_text(t)
print("Inlined", len(json.loads(data)["text"]), "Arabic strings")
