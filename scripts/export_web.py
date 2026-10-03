"""Export the trained model + lexicon + taxonomy to JSON for the in-browser engine (site/assets/js/engine.js).

    python scripts/export_web.py [--lang en]

Writes:
  site/assets/model/<lang>.json   everything the JS engine needs to reproduce triage() exactly
  site/assets/data/eval.json      per-message scores for the site's threshold explorer
"""

from __future__ import annotations

import argparse
import json

import numpy as np
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from scam_triage import lexicons, signals, triage as triage_mod
from scam_triage.dataset import DATA_DIR, ROOT, load_split, read_jsonl
from scam_triage.model import TriageModel
from scam_triage.taxonomy import ALL_LABELS, get_scam_type

SITE = ROOT / "site" / "assets"
TYPE_PRUNE = 0.003  # type-model weights below this magnitude are dropped (parity is checked by tests)


def _round(xs, nd=7) -> list[float]:
    return [float(f"{x:.{nd}g}") for x in xs]


def export_model(lang: str) -> dict:
    m = TriageModel.load(lang=lang)
    f = m.featurizer
    lex = lexicons.load(lang)

    def vocab(vec) -> list[str]:
        terms = [""] * len(vec.vocabulary_)
        for t, i in vec.vocabulary_.items():
            terms[i] = t
        return terms

    coef_t = m.type_clf.coef_
    keep = np.where(np.abs(coef_t).max(axis=0) > TYPE_PRUNE)[0]
    return {
        "lang": lang,
        "version": m.meta.get("version"),
        "trained_at": m.meta.get("trained_at"),
        "thresholds": m.thresholds,
        "fpr_thresholds": m.meta.get("fpr_thresholds", {}),
        "regex": {
            "url": signals.URL_RE.pattern,
            "phone": signals.PHONE_RE.pattern,
            "amount": signals.AMOUNT_RE.pattern,
            "reference": signals._REFERENCE_RE.pattern,
            "negation": signals._NEGATION_RE.pattern,
            "token": f.word.token_pattern,
        },
        "zero_width": "​‌‍⁠﻿",
        "url_shorteners": sorted(signals.URL_SHORTENERS),
        "risky_tlds": sorted(signals.RISKY_TLDS),
        "negatable": sorted(signals.NEGATABLE),
        "signal_ids": list(f.signal_names),
        "patterns": lex.PATTERNS,
        "reasons": lex.REASONS,
        "imitated_brands": lex.IMITATED_BRANDS,
        "lure_words": lex.LURE_WORDS,
        "word": {"ngram_range": list(f.word.ngram_range), "vocab": vocab(f.word), "idf": _round(f.word.idf_)},
        "char": {"ngram_range": list(f.char.ngram_range), "vocab": vocab(f.char), "idf": _round(f.char.idf_)},
        "signal_weight": 1.0,
        "risk": {"intercept": float(m.risk_clf.intercept_[0]), "coef": _round(m.risk_clf.coef_[0])},
        "type": {
            "classes": list(m.type_clf.classes_),
            "intercept": _round(m.type_clf.intercept_),
            "index": keep.tolist(),
            "coef": [_round(coef_t[:, j], 5) for j in keep],
        },
        "stop_words": sorted(ENGLISH_STOP_WORDS),
        "context_signals": sorted(triage_mod.CONTEXT_SIGNALS),
        "max_reasons": triage_mod.MAX_REASONS,
        "max_phrases": triage_mod.MAX_PHRASES,
        "taxonomy": {
            lab: {"label": st.label, "description": st.description, "next_steps": st.next_steps}
            for lab in ALL_LABELS
            for st in [get_scam_type(lab, lang)]
        },
    }


def export_eval(lang: str) -> dict:
    """Per-message scores so the site can recompute recall/FPR at any threshold."""
    m = TriageModel.load(lang=lang)
    sets = {"test": load_split("test", lang)}
    for path in sorted((DATA_DIR / lang).glob("challenge*.jsonl")):
        sets[path.stem] = read_jsonl(path)
    out = {"thresholds": m.thresholds, "sets": {}}
    for name, rows in sets.items():
        scores = m.risk_scores([r["text"] for r in rows])
        out["sets"][name] = {
            "y": [int(r["is_scam"]) for r in rows],
            "s": [round(float(s), 5) for s in scores],
            "src": [r["source"] for r in rows],
        }
    # Readable examples for the site (blind v3 set, which is already public in the repo).
    v3 = read_jsonl(DATA_DIR / lang / "challenge_v3.jsonl")
    out["examples"] = [{"text": r["text"], "label": r["label"]} for r in v3]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    args = ap.parse_args()
    for sub, payload in (("model", export_model(args.lang)), ("data", export_eval(args.lang))):
        path = SITE / sub / (f"{args.lang}.json" if sub == "model" else "eval.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
