#!/usr/bin/env python3
"""Original 120 BPM soundtrack + sound design for the Artline reel (no samples, no licences needed).

Reads events.json (frame cues exported by render.mjs) and writes soundtrack.wav.
Music: ambient intro -> drop at the first category (4.5 s) -> groove -> resolve on the end card.
"""
import json
from pathlib import Path
import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile

HERE = Path(__file__).resolve().parent
cue = json.loads((HERE / "events.json").read_text())
SR, FPS = 48000, cue["fps"]
DUR = cue["total"] / FPS
N = int(DUR * SR)
t = np.arange(N) / SR
rng = np.random.default_rng(42)
BEAT = 0.5
marks = {k: f / FPS for f, k in cue["events"] if k in ("drop", "outro")}
GROOVE_START, GROOVE_END = marks["drop"], marks["outro"]   # first category -> end card

def bp(sig, lo, hi, order=2): return sosfilt(butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), sig)
def hp(sig, f, order=2): return sosfilt(butter(order, f, "highpass", fs=SR, output="sos"), sig)
def lp(sig, f, order=2): return sosfilt(butter(order, f, "lowpass", fs=SR, output="sos"), sig)
def env(n, a, d): # attack/exponential decay envelope, seconds
    k = np.arange(n) / SR
    return np.minimum(1, k / max(a, 1e-4)) * np.exp(-k / d)
def place(bus, sig, at, gain=1.0, pan=0.0):
    i = int(at * SR); j = min(N, i + len(sig))
    if i >= N or j <= i: return
    s = sig[: j - i] * gain
    bus[0, i:j] += s * np.sqrt(0.5 * (1 - pan)); bus[1, i:j] += s * np.sqrt(0.5 * (1 + pan))
def saw(freq, n, detune=0.0):
    ph = np.cumsum(np.full(n, freq * (1 + detune)) / SR); return 2 * (ph % 1) - 1
def note(midi): return 440 * 2 ** ((midi - 69) / 12)

music, sfx = np.zeros((2, N)), np.zeros((2, N))

# ---- drums
def kick():
    n = int(0.45 * SR); k = np.arange(n) / SR
    f = 45 + 110 * np.exp(-k / 0.035); ph = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(ph) * env(n, 0.001, 0.16) + 0.25 * hp(rng.standard_normal(n), 3000) * env(n, 0.0005, 0.004)
def clap():
    n = int(0.3 * SR); nz = bp(rng.standard_normal(n), 900, 4000)
    e = sum(env(n, 0.0005, 0.012) * (np.arange(n) >= int(d * SR)) for d in (0, 0.011, 0.022)) + 0.6 * env(n, 0.002, 0.09)
    return nz * e * 0.9
def hat(open_=False):
    n = int((0.18 if open_ else 0.06) * SR); return hp(rng.standard_normal(n), 7000, 4) * env(n, 0.0005, 0.05 if open_ else 0.014)

kicks = []
b = GROOVE_START
while b < GROOVE_END - 0.01:
    kicks.append(b); place(music, kick(), b, 0.95)
    k = round((b - GROOVE_START) / BEAT)
    if k % 2 == 1: place(music, clap(), b, 0.34, 0.05)
    place(music, hat(k % 4 == 3), b + 0.25, 0.22, 0.25)
    place(music, hat(), b + 0.125, 0.07, -0.3); place(music, hat(), b + 0.375, 0.07, -0.3)
    b += BEAT
kicks = np.array(kicks)
# sidechain pump keyed by the kick
duck = np.ones(N)
for kt in kicks:
    i = int(kt * SR); n = min(N - i, int(0.4 * SR)); duck[i:i + n] = np.minimum(duck[i:i + n], 1 - 0.65 * np.exp(-np.arange(n) / SR / 0.11))

# ---- harmony: Am | F | C | G  (bars of 2 s from the drop)
CHORDS = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
ROOTS = [33, 29, 36, 31]
def chord_at(sec):
    if sec < GROOVE_START or sec >= GROOVE_END: return 0
    return int((sec - GROOVE_START) // 2) % 4
pad = np.zeros(N)
seg = int(0.25 * SR)
for s0 in range(0, N, seg):
    n = min(seg, N - s0); ci = chord_at(s0 / SR)
    for m in CHORDS[ci] + [CHORDS[ci][0] + 12]:
        for dt in (-0.006, 0.0, 0.007):
            ph0 = (s0 / SR) * note(m) * (1 + dt)
            ph = ph0 + np.arange(n) / SR * note(m) * (1 + dt)
            pad[s0:s0 + n] += (2 * (ph % 1) - 1) / 12
pad = lp(pad, 1400, 2)
swell = np.clip(t / 2.2, 0, 1) ** 2 * 0.8 + 0.12         # intro swell
tail = np.clip((DUR - t) / 2.2, 0, 1)                      # fade on the end card
pad *= swell * np.where(t >= GROOVE_START, duck, 1) * np.where(t > GROOVE_END, tail, 1)
music += np.vstack([pad, np.roll(pad, 240)]) * 0.34

# bass: off-beat house pump on the chord root
bass = np.zeros(N)
b = GROOVE_START
while b < GROOVE_END - 0.01:
    for off in (0.25,):
        n = int(0.22 * SR); f = note(ROOTS[chord_at(b)] + 12)
        sig = lp(saw(f, n) + 0.5 * np.sin(2 * np.pi * f / 2 * np.arange(n) / SR), 600) * env(n, 0.004, 0.09)
        i = int((b + off) * SR); j = min(N, i + n); bass[i:j] += sig[: j - i]
    b += BEAT
music += np.vstack([bass, bass]) * 0.55

# sub drone in the intro
drone = np.sin(2 * np.pi * 55 * t) * np.clip(t / 1.5, 0, 1) * np.clip((GROOVE_START - t) / 0.4, 0, 1)
music += np.vstack([drone, drone]) * 0.12

# ---- sound effects
def whoosh(dur=0.35, f0=4000, f1=400):
    n = int(dur * SR); nz = rng.standard_normal(n); out = np.zeros(n); blk = 512
    for s in range(0, n, blk):
        u = s / n; fc = f0 * (f1 / f0) ** u
        out[s:s + blk] = bp(nz[s:s + blk], max(80, fc * 0.6), min(20000, fc * 1.6), 1)
    shape = np.sin(np.pi * np.linspace(0, 1, n)) ** 1.5
    return out * shape * 1.4
def boom(f0=95, f1=40, dur=0.6, noise=0.3):
    n = int(dur * SR); k = np.arange(n) / SR; f = f1 + (f0 - f1) * np.exp(-k / 0.06)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.002, dur / 3) + noise * lp(rng.standard_normal(n), 2500) * env(n, 0.001, 0.05)
def metal(dur=0.9):
    n = int(dur * SR); k = np.arange(n) / SR
    return sum(np.sin(2 * np.pi * fr * k) * a for fr, a in ((196, .5), (371, .35), (529, .3), (811, .2), (1190, .12))) * env(n, 0.001, 0.25)
def click(f=2600, dur=0.012):
    n = int(dur * SR); return np.sin(2 * np.pi * f * np.arange(n) / SR) * env(n, 0.0003, 0.003)
def pop():
    n = int(0.09 * SR); k = np.arange(n) / SR; f = 380 + 600 * np.exp(-k / 0.012)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * env(n, 0.001, 0.03)
def riser(dur):
    n = int(dur * SR); k = np.arange(n) / SR; u = k / dur
    tone = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (u * 2.6)) / SR) * 0.35
    nz = hp(rng.standard_normal(n), 2000) * 0.25
    return (tone + nz) * u ** 2.2
def shimmer():
    out = np.zeros(int(1.2 * SR))
    for i, m in enumerate((88, 93, 96, 100)):
        n = len(out) - int(i * 0.06 * SR); s = np.sin(2 * np.pi * note(m) * np.arange(n) / SR) * env(n, 0.002, 0.35)
        out[int(i * 0.06 * SR):] += s * 0.3
    return out

for f, kind in cue["events"]:
    at = f / FPS
    if kind == "sweep": place(sfx, whoosh(0.45, 300, 6000), at, 0.55, -0.6); place(sfx, whoosh(0.45, 300, 6000), at + 0.05, 0.35, 0.6)
    elif kind == "snap": place(sfx, click(1400, 0.03), at, 0.6); place(sfx, boom(140, 70, 0.2, 0.2), at, 0.4)
    elif kind == "riser": place(sfx, riser(54 / FPS - at), at, 0.5)
    elif kind == "lock": place(sfx, boom(110, 38, 0.9, 0.35), at, 0.95); place(sfx, metal(), at, 0.35)
    elif kind == "shimmer": place(sfx, shimmer(), at, 0.5, 0.2)
    elif kind == "whoosh": place(sfx, whoosh(0.32, 5000, 350), at - 0.12, 0.45, (f % 3 - 1) * 0.5)
    elif kind == "swoosh": place(sfx, whoosh(0.25, 600, 6000), at, 0.32, 0.3)
    elif kind == "hit": place(sfx, boom(120, 45, 0.45, 0.4), at, 0.85); place(sfx, clap(), at, 0.25)
    elif kind == "bighit": place(sfx, boom(140, 36, 0.9, 0.5), at, 1.0); place(sfx, metal(0.7), at, 0.3); place(sfx, clap(), at, 0.4)
    elif kind == "stamp": place(sfx, boom(150, 42, 0.7, 0.6), at, 0.9); place(sfx, metal(0.5), at, 0.25); place(sfx, click(900, 0.04), at, 0.5)
    elif kind == "impact": place(sfx, boom(120, 38, 0.8, 0.4), at, 0.9)
    elif kind == "tick": place(sfx, click(3000), at, 0.45)
    elif kind == "pop": place(sfx, pop(), at, 0.38, ((f * 7) % 5 - 2) * 0.3)
    elif kind == "type":
        for i in range(6): place(sfx, click(4200 + 300 * (i % 3), 0.006), at + i * 0.028, 0.16, 0.4)

# ---- space: shared reverb on pad + effects
def reverb(sig, secs=1.4, wet=0.22):
    n = int(secs * SR); ir = rng.standard_normal((2, n)) * np.exp(-np.arange(n) / SR / (secs / 4)); ir[:, :200] = 0
    out = np.vstack([fftconvolve(sig[c], ir[c])[:N] for c in range(2)]) / np.sqrt(n) * 3
    return sig + wet * out
sfx = reverb(sfx, 1.2, 0.25)
music = music * 0.9

mix = music + sfx
mix[:, : int(0.02 * SR)] *= np.linspace(0, 1, int(0.02 * SR))
end = int(0.3 * SR); mix[:, -end:] *= np.linspace(1, 0, end)
mix = np.tanh(mix * 1.3) / np.tanh(1.3)
mix *= 0.93 / np.max(np.abs(mix))
wavfile.write(HERE / "soundtrack.wav", SR, (mix.T * 32767).astype(np.int16))
print("Wrote", HERE / "soundtrack.wav", f"{DUR:.1f}s")
