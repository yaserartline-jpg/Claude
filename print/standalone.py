#!/usr/bin/env python3
"""Build Artline-Company-Profile.html: the website as ONE self-contained file (all photos and logos embedded),
for sharing by email/WhatsApp or opening offline. Includes the Arabic toggle. Run after website updates."""
import base64, io, re
from pathlib import Path
from PIL import Image
root = Path(__file__).resolve().parent.parent
src = (root / "artline-profile.html").read_text()

def data_uri(rel):
    p = root / rel
    if p.suffix.lower() == ".svg":
        return "data:image/svg+xml;base64," + base64.b64encode(p.read_bytes()).decode()
    im = Image.open(p)
    if p.suffix.lower() == ".png":            # logos: keep transparency, cap size
        im.thumbnail((600, 600), Image.LANCZOS); buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()
    im = im.convert("RGB"); im.thumbnail((1400, 1400), Image.LANCZOS); buf = io.BytesIO()
    im.save(buf, "JPEG", quality=80, optimize=True, progressive=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

# every image file the page can show (static tags plus logos the script builds)
files = sorted({str(p.relative_to(root)) for p in (root / "artline-img").rglob("*") if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".svg") and "enhanced" not in p.parts})
used = [f for f in files if f in src or f.startswith(("artline-img/clients/", "artline-img/partners/"))]
uris = {f: data_uri(f) for f in used}

out = src
for f, u in uris.items():                       # static references
    out = out.replace(f'"{f}"', f'"{u}"')
# logos inserted by the page script get their embedded copy after the page has built them
lookup = "{" + ",".join(f'"{f}":"{u}"' for f, u in uris.items() if f.startswith(("artline-img/clients/", "artline-img/partners/"))) + "}"
out = out.replace("</script>", f'''
// standalone file: swap logo paths for embedded copies, hide the PDF download (shared separately)
(() => {{ const E = {lookup};
  document.querySelectorAll("img").forEach(i => {{ const s = i.getAttribute("src"); if (E[s]) i.src = E[s]; }});
  const dl = document.getElementById("pdf-dl"); if (dl) dl.remove(); }})();
</script>''', 1) if out.count("</script>") == 1 else out[:out.rindex("</script>")] + f'''
// standalone file: swap logo paths for embedded copies, hide the PDF download (shared separately)
(() => {{ const E = {lookup};
  document.querySelectorAll("img").forEach(i => {{ const s = i.getAttribute("src"); if (E[s]) i.src = E[s]; }});
  const dl = document.getElementById("pdf-dl"); if (dl) dl.remove(); }})();
''' + out[out.rindex("</script>"):]
doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
       '<meta name="viewport" content="width=device-width,initial-scale=1"></head><body>' + out + "</body></html>")
left = sorted(set(re.findall(r'"(artline-img/[^"]+)"', doc)))
(root / "Artline-Company-Profile.html").write_text(doc)
print(f"Built Artline-Company-Profile.html: {len(uris)} images embedded, {len(doc)/1e6:.1f} MB; unresolved: {left}")
