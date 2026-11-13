"""Cinematic music for Silent Discipline, made by code (no copyright issues).
Builds with the story: deep braam + boom on the hook, soft piano, strings swell, slow war drums in the middle,
a riser into the last line, a big impact on the last line, then the piano fades out.
Usage: python music.py spec.json out.wav
"""
import json
import random
import sys
import wave

import numpy as np

spec = json.load(open(sys.argv[1]))
OUT = sys.argv[2]
SR = 48000
TOTAL = float(spec["total"])
starts = spec["line_starts"]
rng = random.Random(spec.get("seed", 3))
N = int(TOTAL * SR) + SR
L = np.zeros(N, np.float32)
R = np.zeros(N, np.float32)
t_all = np.arange(N) / SR


def put(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N:
        return
    sig = sig[: N - i] * gain
    L[i:i + len(sig)] += sig * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * (1 + min(0, pan))


def env_exp(n, k):
    return np.exp(-k * np.arange(n) / SR).astype(np.float32)


def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x)
    fr = np.fft.rfftfreq(len(x), 1 / SR)
    m = np.ones_like(fr)
    if lo:
        m *= 1 / (1 + (lo / np.maximum(fr, 1)) ** 4)
    if hi:
        m *= 1 / (1 + (fr / hi) ** 4)
    return np.fft.irfft(X * m, len(x)).astype(np.float32)


def piano(f, dur=3.0, vel=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n, np.float32)
    for k in range(1, 7):
        fk = f * k * (1 + 0.0004 * k * k)
        s += (1 / k ** 1.4) * np.sin(2 * np.pi * fk * t) * np.exp(-t * (1.6 + 0.9 * k))
    att = np.minimum(1, t / 0.004)
    return (s * att * vel * 0.35).astype(np.float32)


def pad(freqs, dur, bright=0.5):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n, np.float32)
    for f in freqs:
        for det in (0.997, 1.003):
            for k in range(1, 7):
                s += (bright ** (k - 1)) / k * np.sin(2 * np.pi * f * det * k * t + rng.random() * 6)
    a = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / 1.0)
    return (s * a * 0.035).astype(np.float32)


def tom(dur=1.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 55 + 70 * np.exp(-t * 18)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 3.2) + 0.25 * np.random.uniform(-1, 1, n) * np.exp(-t * 30)
    return (s * 0.8).astype(np.float32)


def boom(dur=3.0, big=1.0):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = 32 + 40 * np.exp(-t * 6)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    noise = fft_filter(np.random.uniform(-1, 1, n).astype(np.float32), hi=900) * np.exp(-t * 4)
    return ((s + 0.6 * noise) * big).astype(np.float32)


def braam(dur=2.6):
    n = int(dur * SR)
    t = np.arange(n) / SR
    s = np.zeros(n, np.float32)
    bright = np.minimum(1, t / 0.6) * np.exp(-t * 0.9)
    for f in (55, 82.41, 110):
        for k in range(1, 14):
            s += np.sin(2 * np.pi * f * k * t) / k * (bright ** (k * 0.35))
    return (s * np.exp(-t * 1.1) * 0.22).astype(np.float32)


def whoosh(dur=1.0, rise=True):
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = (t / dur) ** 2 if rise else np.exp(-t * 5)
    x = fft_filter(np.random.uniform(-1, 1, n).astype(np.float32), lo=500, hi=7000)
    return (x * e * 0.5).astype(np.float32)


def riser(dur=1.3):
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = (t / dur) ** 3
    ph = 2 * np.pi * np.cumsum(220 + 500 * (t / dur) ** 2) / SR
    x = fft_filter(np.random.uniform(-1, 1, n).astype(np.float32), lo=900, hi=5000) * 0.35 + 0.35 * np.sin(ph)
    return (x * e * 0.4).astype(np.float32)


# ---------- harmony ----------
key = rng.choice([1.0, 1.0595, 0.9439])
A, F_, C, G, E = 110 * key, 87.31 * key, 130.81 * key, 98 * key, 82.41 * key
prog = rng.choice([[(A, 1.1892), (F_, 1.2599), (C, 1.2599), (G, 1.2599)], [(A, 1.1892), (E, 1.1892), (F_, 1.2599), (G, 1.2599)]])
BEAT = 60 / 68
BAR = BEAT * 4
last = starts[-1]
mid = starts[len(starts) // 2]

# intro hit
put(braam(), 0.0, 1.0)
put(boom(3.2, 1.0), 0.0, 0.9)
put(whoosh(0.6, False), 0.0, 0.6)

# chords: pad from line 2, piano melody all along
bars = int(TOTAL / BAR) + 2
for b in range(bars):
    at = 0.4 + b * BAR
    if at > TOTAL - 0.5:
        break
    root, third = prog[b % 4]
    chord = [root * 2, root * 2 * third, root * 2 * 1.4983]
    if at >= starts[min(1, len(starts) - 1)] - 0.5:
        bright = 0.35 + 0.35 * min(1, at / max(1, last))
        put(pad(chord, BAR + 0.8, bright), at, 1.4 + 1.0 * min(1, at / max(1, last)))
    put(piano(root, 4.0, 0.55), at, 1.0)  # low note
    scale = [root * 4, root * 4 * third, root * 4 * 1.4983, root * 8, root * 4 * 1.335]
    for beat in range(4):
        if beat == 0 or rng.random() < 0.7:
            note = rng.choice(scale)
            put(piano(note, 2.5, 0.55 + 0.2 * rng.random()), at + beat * BEAT, 1.3, pan=rng.uniform(-0.4, 0.4))

# war drums from the middle line until the last line
tt = mid
while tt < last - 0.2:
    put(tom(), tt, 0.55)
    put(tom(1.2), tt + BEAT * 1.5, 0.3, pan=0.3)
    tt += BEAT * 2

# riser into the last line, then the big impact
put(riser(1.3), max(0.5, last - 1.3), 0.8)
put(boom(3.5, 1.3), last, 1.0)
put(braam(3.0), last, 0.8)
put(fft_filter(np.random.uniform(-1, 1, int(1.5 * SR)).astype(np.float32), lo=3000, hi=9000) * env_exp(int(1.5 * SR), 3.5) * 0.15, last, 1.0)

# ---------- reverb (convolution with a decaying-noise room) ----------
ir_n = int(2.8 * SR)
ir = np.random.uniform(-1, 1, ir_n).astype(np.float32) * np.exp(-np.arange(ir_n) / SR * 2.4)
ir[0] = 0
ir /= np.abs(ir).sum() / 6


def conv(x):
    n = len(x) + ir_n
    size = 1 << (n - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, size) * np.fft.rfft(ir, size), size)[: len(x)]
    return y.astype(np.float32)


L2 = L + 0.35 * conv(L)
R2 = R + 0.35 * conv(R)
fade = np.ones(N, np.float32)
fs = int((TOTAL - 1.4) * SR)
fade[fs:] = np.linspace(1, 0, N - fs)
L2 *= fade
R2 *= fade
peak = max(np.abs(L2).max(), np.abs(R2).max(), 1e-6)
st = np.stack([L2, R2], 1) / peak * 0.9
st = st[: int(TOTAL * SR)]
with wave.open(OUT, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((st * 32767).astype(np.int16).tobytes())
