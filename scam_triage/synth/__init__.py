"""Synthetic labelled message generator.

Fills per-language templates with randomized slots, applies light noise
(casing, text-speak, typos, emoji) and splits by *template*, so validation and
test messages come from phrasings the model never saw during training.
"""

from __future__ import annotations

import math
import random
import re
from importlib import import_module
from types import ModuleType

_SLOT_RE = re.compile(r"\{(\w+)\}")
_TEXTSPEAK = {r"\byou\b": "u", r"\bplease\b": "pls", r"\bare\b": "r", r"\btonight\b": "2nite", r"\bthanks\b": "thx"}
_EMOJI = ["🙏", "😊", "⚠️", "❗", "😩", "👍", "🚨", "📦", "💰"]


def load_templates(lang: str) -> ModuleType:
    return import_module(f"{__name__}.{lang}")


def fill(template: str, slots: dict[str, object], rng: random.Random, begin=None) -> str:
    if begin is not None:
        begin(rng)

    def sub(m: re.Match[str]) -> str:
        source = slots[m.group(1)]
        return source(rng) if callable(source) else rng.choice(source)  # type: ignore[arg-type]

    return _SLOT_RE.sub(sub, template)


def augment(text: str, rng: random.Random) -> str:
    if rng.random() < 0.15:
        for pat, rep in _TEXTSPEAK.items():
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)
    if rng.random() < 0.1:
        words = text.split(" ")
        i = rng.randrange(len(words))
        w = words[i]
        if len(w) > 4 and w.isalpha():
            j = rng.randrange(len(w) - 1)
            words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2 :]
        text = " ".join(words)
    if rng.random() < 0.15:
        text = text.lower()
    elif rng.random() < 0.04:
        text = text.upper()
    if rng.random() < 0.2:
        text = text.rstrip(".!")
    if rng.random() < 0.08:
        text = f"{text} {rng.choice(_EMOJI)}"
    return text


def split_templates(n: int, rng: random.Random, test_frac: float = 0.2, val_frac: float = 0.15) -> dict[int, str]:
    """Assign template indices to train/val/test (at least 2 in each held-out split)."""
    idx = list(range(n))
    rng.shuffle(idx)
    n_test = max(2, round(n * test_frac))
    n_val = max(2, round(n * val_frac))
    return {i: ("test" if k < n_test else "val" if k < n_test + n_val else "train") for k, i in enumerate(idx)}


def generate(lang: str = "en", seed: int = 13, scam_per_label: int = 360, legit_total: int = 3000) -> list[dict]:
    """Generate a de-duplicated, template-split synthetic corpus."""
    mod = load_templates(lang)
    rng = random.Random(seed)
    rows: list[dict] = []
    seen: set[str] = set()
    for label, templates in mod.TEMPLATES.items():
        target = legit_total if label == "legit" else scam_per_label
        per_template = math.ceil(target / len(templates))
        assignment = split_templates(len(templates), rng)
        for t_idx, template in enumerate(templates):
            made, attempts = 0, 0
            while made < per_template and attempts < per_template * 20:
                attempts += 1
                text = augment(fill(template, mod.SLOTS, rng, getattr(mod, "begin_message", None)), rng)
                if text in seen:
                    continue
                seen.add(text)
                made += 1
                rows.append({
                    "id": f"{lang}-syn-{len(rows):06d}",
                    "text": text,
                    "label": label,
                    "is_scam": int(label != "legit"),
                    "template_id": f"{label}/{t_idx:02d}",
                    "split": assignment[t_idx],
                    "source": "synthetic",
                    "lang": lang,
                })
    return rows
