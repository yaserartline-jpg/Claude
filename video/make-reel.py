#!/usr/bin/env python3
"""Artline portfolio reel: 1080x1920 (9:16), 30 fps, 30 s -> artline-reel.mp4

Edit PROJECTS / STATS / CONTACT below, then run:  python3 video/make-reel.py
Palette: #000 #FFF #4D4D4D #808080 #D9D9D9 #800000 only.
"""
import math, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "artline-img"
FONTS = Path(__file__).resolve().parent / "fonts"
OUT = ROOT / "video" / "artline-reel.mp4"

# ---- Content (edit here) -------------------------------------------------
PROJECTS = [  # (photo, meta line, title, caption)
    ("p-ikea.jpg", "Retail · 2024", "IKEA", "Store fit-out and maintenance"),
    ("p-mcdonalds.jpg", "F&B · 2024", "McDonald's", "Food court restaurant interior"),
    ("p-tawjeeh-2.jpg", "Government", "Tawjeeh service centre", "Service hall with custom curved counters"),
    ("p-banobagi-2.jpg", "Healthcare", "Banobagi Dermatology Clinic", "Clinic interior fit-out"),
    ("p-deyaar.jpg", "Corporate · 2025", "Deyaar head office", "Head office fit-out and shopfront"),
    ("p-sparkys-2.jpg", "Leisure · 2024", "Sparkys Land", "Family entertainment centre"),
    ("p-soco-young-2.jpg", "Education · 2026", "SOCO Kids & SOCO Young", "Interior fit-out and VRF air-conditioning"),
]
STATS = [("15+", "years of fit-out & construction"), ("50", "projects delivered since 2021"), ("33", "government & corporate clients")]
ISO_LINE = "ISO 9001 · ISO 14001 · ISO 45001"
CONTACT = ["+971 50 299 0358", "info@artline-uae.com", "artline-uae.com"]
EYEBROW = "UNITED ARAB EMIRATES · SINCE 2009"
PROMISE = "DESIGNED, BUILT AND FURNISHED BY ONE TEAM."

# ---- Setup ---------------------------------------------------------------
W, H, FPS = 1080, 1920, 30
BLACK, WHITE, DARK, MID, LIGHT, MAROON = (0, 0, 0), (255, 255, 255), (77, 77, 77), (128, 128, 128), (217, 217, 217), (128, 0, 0)

def font(name, size, weight=None):
    f = ImageFont.truetype(str(FONTS / name), size)
    if weight:
        f.set_variation_by_axes([weight])
    return f

BARLOW = lambda s: font("BarlowCondensed-Bold.ttf", s)
BARLOW_SB = lambda s: font("BarlowCondensed-SemiBold.ttf", s)
MONO = lambda s: font("IBMPlexMono-Medium.ttf", s)
SANS = lambda s: font("SourceSans3[wght].ttf", s, 400)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(t): t = clamp(t); return 1 - (1 - t) ** 3
def prog(f, start, dur): return clamp((f - start) / dur)

# Line art from the website, re-used as the backdrop
html = (ROOT / "artline-profile.html").read_text()
sym = html[html.index('<symbol id="lineart"'):html.index("</symbol>")]
SHAPES = []
for kind, pts in re.findall(r'<(polyline|polygon) points="([^"]+)"', sym):
    p = [tuple(map(float, xy.split(","))) for xy in pts.split()]
    if kind == "polygon": p.append(p[0])
    SHAPES.append(p)

def lineart_layer(amount, flip=False, y0=0, scale=1.25):
    """Line art drawn to `amount` (0..1) of each path; 2x supersampled."""
    S = 2
    im = Image.new("RGB", (W * S, H * S), BLACK)
    d = ImageDraw.Draw(im)
    for p in SHAPES:
        pts = [((1200 - x if flip else x) * scale * S - 120 * S, (y * scale + y0) * S) for x, y in p]
        segs = list(zip(pts, pts[1:]))
        total = sum(math.dist(a, b) for a, b in segs)
        left = total * amount
        for a, b in segs:
            L = math.dist(a, b)
            if left <= 0: break
            if left < L:
                b = (a[0] + (b[0] - a[0]) * left / L, a[1] + (b[1] - a[1]) * left / L)
            d.line([a, b], fill=DARK, width=3 * S // 2)
            left -= L
    return im.resize((W, H), Image.LANCZOS)

def backdrop(amount=1.0):
    top = lineart_layer(amount, False, -60)
    bot = lineart_layer(amount, True, 1300)
    return Image.composite(top, bot, Image.linear_gradient("L").resize((W, H)).point(lambda v: 255 if v < 128 else 0))

BG_FULL = backdrop(1.0)
LOGO = Image.open(IMG / "logo-full-white.png").convert("RGBA")

def paste_logo(im, size, cx, cy, alpha=1.0):
    lg = LOGO.resize((size, size), Image.LANCZOS)
    if alpha < 1:
        a = lg.getchannel("A").point(lambda v: int(v * alpha)); lg.putalpha(a)
    im.paste(lg, (int(cx - size / 2), int(cy - size / 2)), lg)

def text(d, xy, s, f, fill, anchor="la", alpha=1.0, bg=BLACK):
    if alpha < 1: fill = tuple(int(b + (c - b) * alpha) for c, b in zip(fill, bg))
    d.text(xy, s, font=f, fill=fill, anchor=anchor)

def fit_lines(s, f_for, max_w, sizes):
    """Largest size from `sizes` that fits `s` in max 2 lines of max_w."""
    for sz in sizes:
        f = f_for(sz); words = s.split(); lines = [""]
        for w_ in words:
            t = (lines[-1] + " " + w_).strip()
            if f.getlength(t) <= max_w: lines[-1] = t
            else: lines.append(w_)
        if len(lines) <= 2 and all(f.getlength(l) <= max_w for l in lines): return f, sz, lines
    return f, sz, lines

def cover(img, w, h, zoom=1.0):
    r = max(w / img.width, h / img.height) * zoom
    im = img.resize((math.ceil(img.width * r), math.ceil(img.height * r)), Image.LANCZOS)
    x, y = (im.width - w) // 2, (im.height - h) // 2
    return im.crop((x, y, x + w, y + h))

PHOTOS = [Image.open(IMG / p[0]).convert("RGB") for p in PROJECTS]

# ---- Timeline (frames) ---------------------------------------------------
T_INTRO, T_HEAD = 0, 90                     # 0-3 s logo, 3-5.5 s headline
T_PROJ, PER = 165, 70                       # 7 x 2.33 s
T_STATS = T_PROJ + PER * len(PROJECTS)      # ~21.8 s
T_END = T_STATS + 120                       # 4 s stats, then end card
TOTAL = 900

def wipe(im, f, t0):
    """Maroon band sweeping across the frame around a scene cut at t0."""
    p = (f - (t0 - 7)) / 14
    if 0 <= p <= 1:
        x = int(-W + p * 2 * W)
        ImageDraw.Draw(im).rectangle([x, 0, x + W, H], fill=MAROON)

def scene_intro(f):
    im = backdrop(ease(prog(f, 0, 40))) if f < 40 else BG_FULL.copy()
    a = ease(prog(f, 18, 30))
    paste_logo(im, int(420 + 40 * a), W / 2, 820, a)
    d = ImageDraw.Draw(im)
    text(d, (W / 2, 1150), EYEBROW, MONO(30), LIGHT, "mm", ease(prog(f, 45, 20)))
    return im

def scene_head(f):
    im = BG_FULL.copy(); d = ImageDraw.Draw(im); t = f - T_HEAD
    F = BARLOW(150); x = 80; y = 560
    for i, line in enumerate(["FIT-OUT &", "CONSTRUCTION", "FOR THE UAE'S"]):
        p = ease(prog(t, 4 + i * 5, 14))
        text(d, (x, y + i * 150 + (1 - p) * 40), line, F, WHITE, "ls", p)
    # maroon bar + LEADING BRANDS
    p = ease(prog(t, 20, 14)); by = y + 3 * 150
    bw = F.getlength("LEADING BRANDS") + 40
    if p > 0: d.rectangle([x - 14, by - 132, x - 14 + bw * p, by + 22], fill=MAROON)
    text(d, (x + 6, by), "LEADING BRANDS", F, WHITE, "ls", ease(prog(t, 28, 10)), MAROON)
    p = ease(prog(t, 36, 14))
    if p > 0:
        d.rectangle([x, by + 110, x + 6, by + 170], fill=MAROON)
        fp = BARLOW_SB(46)
        text(d, (x + 30, by + 152), PROMISE, fp, WHITE, "ls", p)
    return im

def scene_project(f):
    i = (f - T_PROJ) // PER; t = (f - T_PROJ) % PER
    photo, meta, title, cap = PROJECTS[i]
    im = BG_FULL.copy(); d = ImageDraw.Draw(im)
    paste_logo(im, 150, 80 + 75, 200)
    text(d, (W - 80, 200), f"{i + 1:02d} / {len(PROJECTS):02d}", MONO(32), LIGHT, "rm")
    # photo panel with slow push-in, revealed by a maroon wipe
    py, ph = 380, 940
    pic = cover(PHOTOS[i], W, ph, 1.0 + 0.07 * (t / PER))
    rv = ease(prog(t, 0, 12))
    cut = int(W * rv)
    if cut > 0: im.paste(pic.crop((0, 0, cut, ph)), (0, py))
    if rv < 1: d.rectangle([cut, py, min(W, cut + 60), py + ph], fill=MAROON)
    # text block
    tx, ty = 80, py + ph + 70
    p1 = ease(prog(t, 8, 12))
    text(d, (tx, ty + (1 - p1) * 20), meta.upper(), MONO(32), LIGHT, "ls", p1)
    p2 = ease(prog(t, 10, 14))
    if p2 > 0: d.rectangle([tx, ty + 26, tx + 70 * p2, ty + 32], fill=MAROON)
    F, sz, lines = fit_lines(title.upper().replace("MCD", "McD"), BARLOW, W - 160, [116, 104, 92, 80])
    p3 = ease(prog(t, 12, 14))
    yy = ty + 40 + sz
    for k, ln in enumerate(lines):
        text(d, (tx, yy + k * (sz * 0.98) + (1 - p3) * 30), ln, F, WHITE, "ls", p3)
    yy += (len(lines) - 1) * sz * 0.98 + 66
    text(d, (tx, yy), cap, SANS(42), LIGHT, "ls", ease(prog(t, 18, 14)))
    return im

def scene_stats(f):
    im = BG_FULL.copy(); d = ImageDraw.Draw(im); t = f - T_STATS
    y = 520
    for i, (num, label) in enumerate(STATS):
        p = ease(prog(t, 6 + i * 12, 22))
        n = int(re.sub(r"\D", "", num)); suffix = num[len(str(n)):]
        shown = f"{round(n * p)}{suffix}" if p < 1 else num
        text(d, (80, y + (1 - p) * 30), shown, BARLOW(240), WHITE, "ls", min(1, p * 2))
        if p > 0: d.rectangle([84, y + 30, 84 + 90 * p, y + 38], fill=MAROON)
        text(d, (80, y + 100), label, SANS(46), LIGHT, "ls", p)
        y += 400
    text(d, (80, y - 120), ISO_LINE, MONO(34), LIGHT, "ls", ease(prog(t, 50, 16)))
    return im

def scene_end(f):
    im = BG_FULL.copy(); t = f - T_END
    a = ease(prog(t, 4, 20))
    paste_logo(im, int(460 + 20 * a), W / 2, 640, a)
    d = ImageDraw.Draw(im)
    text(d, (W / 2, 990), PROMISE, BARLOW_SB(44), WHITE, "mm", ease(prog(t, 16, 14)))
    for k, c in enumerate(CONTACT):
        text(d, (W / 2, 1110 + k * 70), c, MONO(40), LIGHT, "mm", ease(prog(t, 24 + k * 5, 14)))
    p = ease(prog(t, 42, 14))
    if p > 0:
        bw, bh = 640, 112; x0 = (W - bw) / 2; y0 = 1380
        d.rectangle([x0, y0, x0 + bw * p, y0 + bh], fill=MAROON)
        text(d, (W / 2, y0 + bh / 2), "REQUEST A SITE VISIT", BARLOW(56), WHITE, "mm", ease(prog(t, 50, 10)), MAROON)
    return im

def frame(f):
    if f < T_HEAD: im = scene_intro(f)
    elif f < T_PROJ: im = scene_head(f)
    elif f < T_STATS: im = scene_project(f)
    elif f < T_END: im = scene_stats(f)
    else: im = scene_end(f)
    for cut in (T_HEAD, T_PROJ, T_STATS, T_END): wipe(im, f, cut)
    return im

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--stills":   # preview frames
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for f in map(int, sys.argv[3].split(",")):
            frame(f).save(out / f"f{f:03d}.png")
        sys.exit()
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], stdin=subprocess.PIPE)
    for f in range(TOTAL):
        ff.stdin.write(frame(f).tobytes())
    ff.stdin.close(); ff.wait()
    print("Built", OUT)
