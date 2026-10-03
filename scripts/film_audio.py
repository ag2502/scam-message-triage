"""Synthesize the film soundtrack (music + sound effects) from the film's cue list.

Pure NumPy/SciPy: no samples, no external audio. Used by scripts/record_demo.py; can also run alone:
    python scripts/film_audio.py out.wav   (uses the cues hard-coded in a quick test)
"""

from __future__ import annotations

import sys
import wave

import numpy as np
from scipy.signal import butter, sosfilt

SR = 48000
RNG = np.random.default_rng(7)

# i - VI - III - VII in C minor, one chord per 2 bars at 96 bpm (5 s).
CHORDS = [
    [130.81, 155.56, 196.00, 261.63],  # Cm
    [103.83, 130.81, 155.56, 207.65],  # Ab
    [155.56, 196.00, 233.08, 311.13],  # Eb
    [116.54, 146.83, 174.61, 233.08],  # Bb
]
ROOTS = [65.41, 51.91, 77.78, 58.27]


def t_axis(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def env_adsr(n: int, a: float, r: float) -> np.ndarray:
    e = np.ones(n)
    na, nr = int(a * SR), int(r * SR)
    if na: e[:na] = np.linspace(0, 1, na)
    if nr: e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, hz, "low", fs=SR, output="sos"), x)


def highpass(x: np.ndarray, hz: float, order: int = 2) -> np.ndarray:
    return sosfilt(butter(order, hz, "high", fs=SR, output="sos"), x)


def sweep_filter(x: np.ndarray, f0: float, f1: float, f2: float | None = None) -> np.ndarray:
    """Time-varying one-pole low-pass whose cutoff glides f0 -> f1 (-> f2)."""
    n = len(x)
    if f2 is None:
        cut = np.geomspace(f0, f1, n)
    else:
        h = n // 2
        cut = np.concatenate([np.geomspace(f0, f1, h), np.geomspace(f1, f2, n - h)])
    a = 1 - np.exp(-2 * np.pi * cut / SR)
    y = np.empty(n)
    acc = 0.0
    for i in range(n):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def active(spans, t: np.ndarray, fade: float = 0.8) -> np.ndarray:
    g = np.zeros_like(t)
    for a, b in spans:
        g = np.maximum(g, np.clip((t - a) / fade, 0, 1) * np.clip((b - t) / fade, 0, 1))
    return g


# ---------------- music ----------------
def music(dur: float, arr: dict) -> np.ndarray:
    t = t_axis(dur)
    beat = 60 / arr.get("bpm", 96)
    out = np.zeros((len(t), 2))

    # Pad: detuned additive saw per note, chord crossfades, slow movement.
    pad = np.zeros((len(t), 2))
    seg = 8 * beat
    for k, start in enumerate(np.arange(0, dur, seg)):
        chord = CHORDS[k % 4]
        n0, n1 = int(start * SR), min(len(t), int((start + seg + 1.0) * SR))
        tt = t[n0:n1] - start
        e = env_adsr(n1 - n0, 0.9, 1.0)
        for f in chord:
            for det, ch in ((0.997, 0), (1.003, 1)):
                w = sum(np.sin(2 * np.pi * f * det * h * tt + h) / h for h in range(1, 6))
                pad[n0:n1, ch] += 0.05 * w * e
    for ch in range(2):
        pad[:, ch] = lowpass(pad[:, ch], 1400) * (0.85 + 0.15 * np.sin(2 * np.pi * 0.12 * t + ch))
    out += pad * active(arr["pad"], t, 2.0)[:, None]

    # Bass: root eighths with pluck envelope.
    bass = np.zeros(len(t))
    for i, st in enumerate(np.arange(0, dur, beat / 2)):
        root = ROOTS[int(st // seg) % 4]
        n0 = int(st * SR); n1 = min(len(t), n0 + int(beat / 2 * SR))
        tt = t[n0:n1] - st
        note = np.sin(2 * np.pi * root * tt) + 0.3 * np.sin(2 * np.pi * root * 2 * tt)
        bass[n0:n1] += np.tanh(1.6 * note) * np.exp(-tt * (5 if i % 2 else 3)) * (0.9 if i % 2 == 0 else 0.6)
    out += (0.16 * lowpass(bass, 500) * active(arr["bass"], t))[:, None]

    # Hi-hat pulse: eighth-note noise ticks.
    hat = np.zeros(len(t))
    tick = highpass(RNG.standard_normal(int(0.04 * SR)), 7000) * np.exp(-np.arange(int(0.04 * SR)) / SR * 90)
    for i, st in enumerate(np.arange(0, dur, beat / 2)):
        n0 = int(st * SR)
        if n0 + len(tick) < len(hat): hat[n0:n0 + len(tick)] += tick * (0.9 if i % 2 else 0.5)
    g = active(arr["pulse"], t)
    out[:, 0] += 0.05 * hat * g
    out[:, 1] += 0.05 * np.roll(hat, 90) * g

    # Kick: four on the floor.
    kick = np.zeros(len(t))
    k = kick_sample(0.35, 0.9)
    for st in np.arange(0, dur, beat):
        n0 = int(st * SR)
        if n0 + len(k) < len(kick): kick[n0:n0 + len(k)] += k
    out += (0.22 * kick * active(arr["kick"], t, 0.1))[:, None]

    # Outro: a sustained Cm(add9) swell.
    for a, b in arr.get("outro", []):
        n0, n1 = int(a * SR), min(len(t), int(b * SR))
        tt = t[n0:n1] - a
        e = np.clip(tt / 1.5, 0, 1) * np.clip((b - a - tt) / 2.5, 0, 1)
        for f in (130.81, 196.0, 261.63, 293.66, 311.13, 392.0):
            for ch, det in ((0, 0.998), (1, 1.002)):
                out[n0:n1, ch] += 0.045 * e * lowpass(sum(np.sin(2 * np.pi * f * det * h * tt) / h for h in range(1, 4)), 2400)
    return out


def kick_sample(length: float, gain: float) -> np.ndarray:
    tt = t_axis(length)
    freq = 45 + 75 * np.exp(-tt * 28)
    phase = 2 * np.pi * np.cumsum(freq) / SR
    click = highpass(RNG.standard_normal(len(tt)), 2000) * np.exp(-tt * 300) * 0.3
    return gain * (np.sin(phase) * np.exp(-tt * 7) + click)


# ---------------- sound effects ----------------
def bell(freqs, dur, decay=4.0, gap=0.0, partial=2.76):
    tt = t_axis(dur + gap * len(freqs))
    y = np.zeros(len(tt))
    for i, f in enumerate(freqs):
        s = tt - i * gap
        m = s >= 0
        y[m] += (np.sin(2 * np.pi * f * s[m]) + 0.25 * np.sin(2 * np.pi * f * partial * s[m])) * np.exp(-s[m] * decay) * np.clip(s[m] / 0.004, 0, 1)
    return y


def sfx(kind: str) -> np.ndarray:
    if kind == "notif":
        return 0.5 * bell([1318.5, 1760.0], 0.7, decay=5.5, gap=0.11)
    if kind == "buzz":
        tt = t_axis(0.42)
        return 0.22 * lowpass(np.sign(np.sin(2 * np.pi * 150 * tt)), 400) * env_adsr(len(tt), 0.02, 0.08) * (0.7 + 0.3 * np.sin(2 * np.pi * 28 * tt))
    if kind == "thump":
        return 0.9 * kick_sample(0.6, 1.0) + 0.15 * lowpass(RNG.standard_normal(int(0.6 * SR)), 900) * np.exp(-t_axis(0.6) * 9)
    if kind == "impact":
        tt = t_axis(1.6)
        noise = lowpass(RNG.standard_normal(len(tt)), 3500) * np.exp(-tt * 3.2)
        return 0.9 * np.pad(kick_sample(0.8, 1.2), (0, len(tt) - int(0.8 * SR))) + 0.22 * noise
    if kind == "whoosh":
        n = RNG.standard_normal(int(0.7 * SR))
        y = sweep_filter(n, 250, 3200, 300)
        return 0.55 * y * np.sin(np.linspace(0, np.pi, len(y))) ** 1.5
    if kind == "tap":
        tt = t_axis(0.03)
        return 0.25 * (highpass(RNG.standard_normal(len(tt)), 3000) * np.exp(-tt * 400) + 0.5 * np.sin(2 * np.pi * 2200 * tt) * np.exp(-tt * 250))
    if kind == "send":
        tt = t_axis(0.16)
        f = np.geomspace(500, 1300, len(tt))
        return 0.3 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 18) * np.clip(tt / 0.005, 0, 1)
    if kind == "receive":
        return 0.32 * bell([880.0, 1174.7], 0.3, decay=12, gap=0.07, partial=2.0)
    if kind == "tick":
        tt = t_axis(0.05)
        return 0.18 * np.sin(2 * np.pi * 3000 * tt) * np.exp(-tt * 120)
    if kind == "pop":
        tt = t_axis(0.12)
        f = np.geomspace(380, 950, len(tt))
        return 0.35 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 30) * np.clip(tt / 0.003, 0, 1)
    if kind in ("riser", "riser_short"):
        dur = 2.4 if kind == "riser" else 1.2
        tt = t_axis(dur)
        noise = sweep_filter(RNG.standard_normal(len(tt)), 300, 6000)
        f = np.geomspace(180, 1100, len(tt))
        tone = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
        return 0.35 * (noise + tone) * (tt / dur) ** 2
    if kind == "chime":
        return 0.38 * bell([1046.5, 1318.5, 1568.0, 2093.0], 0.9, decay=5, gap=0.08)
    if kind == "chime_end":
        return 0.3 * bell([523.25, 783.99, 1046.5, 1174.7], 2.6, decay=1.6, gap=0.05)
    if kind.startswith("typing"):
        dur = float(kind.split(":")[1]) if ":" in kind else 1.5
        y = np.zeros(int((dur + 0.1) * SR))
        s = 0.0
        click = sfx("tap") * 0.6
        while s < dur:
            n0 = int(s * SR)
            y[n0:n0 + len(click)] += click * RNG.uniform(0.5, 1.0)
            s += RNG.uniform(0.055, 0.12)
        return y
    raise ValueError(kind)


def render(cues, arrangement: dict, duration: float) -> np.ndarray:
    mix = music(duration, arrangement)
    fx = np.zeros_like(mix)
    for i, (at, kind) in enumerate(cues):
        y = sfx(kind)
        n0 = int(at * SR)
        n1 = min(len(fx), n0 + len(y))
        pan = 0.5 + 0.12 * np.sin(i * 1.7)
        fx[n0:n1, 0] += y[: n1 - n0] * (1 - pan) * 1.6
        fx[n0:n1, 1] += y[: n1 - n0] * pan * 1.6
    out = np.tanh(1.1 * (mix * 1.25 + fx))
    out *= 0.89 / max(1e-9, np.abs(out).max())  # peak about -1 dBFS
    fade = int(0.4 * SR)
    out[-fade:] *= np.linspace(1, 0, fade)[:, None]
    return out


def write_wav(path: str, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


if __name__ == "__main__":
    demo_cues = [(0.5, "notif"), (1.5, "whoosh"), (2.5, "pop"), (3.0, "impact"), (4.5, "chime")]
    arr = {"bpm": 96, "pad": [[0, 8]], "pulse": [[2, 8]], "kick": [[3, 8]], "bass": [[1, 8]], "outro": []}
    write_wav(sys.argv[1] if len(sys.argv) > 1 else "test.wav", render(demo_cues, arr, 8))
