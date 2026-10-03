"""Public entry point: text in, explained verdict out."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from scam_triage.model import TriageModel
from scam_triage.signals import detect
from scam_triage.taxonomy import LEGIT, get_scam_type

MAX_REASONS = 4
MAX_PHRASES = 5

# Context signals describe *what* a message is about; on their own they are not
# suspicious, so they are listed after behavioural signals and hidden on low risk.
CONTEXT_SIGNALS = {"has_link", "money_amount", "payment_rail", "delivery", "bank_mention"}


@dataclass
class TriageResult:
    risk_score: float
    risk_level: str  # low | medium | high
    scam_type: str  # a taxonomy id, or "legit" when risk is low
    scam_type_label: str
    type_confidence: float
    summary: str
    reasons: list[str]
    key_phrases: list[str]
    next_steps: list[str]
    lang: str
    model_version: str

    def to_dict(self) -> dict:
        return asdict(self)


@lru_cache(maxsize=4)
def get_model(lang: str = "en") -> TriageModel:
    return TriageModel.load(lang=lang)


def triage(text: str, lang: str = "en", model: TriageModel | None = None) -> TriageResult:
    model = model or get_model(lang)
    score = float(model.risk_scores([text])[0])
    level = model.level(score)
    classes, probs = model.type_probs([text])
    best = int(probs[0].argmax())
    type_id, type_conf = classes[best], float(probs[0][best])

    # Reasons: fired signals that push this message towards "scam", strongest first.
    contrib = dict(model.contributions(text))
    hits = [h for h in detect(text, lang) if contrib.get(f"signal:{h.id}", 0.0) > 0]
    fired = {h.id for h in hits}
    if "suspicious_link" in fired:
        hits = [h for h in hits if h.id != "has_link"]
    if level == "low":
        hits = [h for h in hits if h.id not in CONTEXT_SIGNALS]
    hits.sort(key=lambda h: (h.id in CONTEXT_SIGNALS, -contrib[f"signal:{h.id}"]))
    reasons = [h.reason for h in hits[:MAX_REASONS]]
    phrases = [name for name, c in contrib.items() if c > 0 and _is_readable_phrase(name)][:MAX_PHRASES]

    if level == "low":
        phrases = []
        shown = get_scam_type(LEGIT, lang)
        summary = "No strong scam patterns found."
        if reasons:
            summary += " A few things are worth double-checking, though."
        return TriageResult(round(score, 4), level, LEGIT, shown.label, round(1 - score, 4), summary,
                            reasons, phrases, shown.next_steps, lang, model.meta.get("version", "?"))

    st = get_scam_type(type_id, lang)
    lead = "This looks like a scam" if level == "high" else "This could be a scam"
    summary = f"{lead}: {st.label.lower()}. {st.description}"
    return TriageResult(round(score, 4), level, type_id, st.label, round(type_conf, 4), summary,
                        reasons, phrases, st.next_steps, lang, model.meta.get("version", "?"))


def _is_readable_phrase(feature: str) -> bool:
    if feature.startswith(("char:", "signal:")) or "__" in feature:
        return False
    words = feature.split()
    return not all(w in ENGLISH_STOP_WORDS or w.startswith("__") or w.isdigit() or len(w) < 3 for w in words)
