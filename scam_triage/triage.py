"""Public entry point: text in, explained verdict out."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from functools import lru_cache

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from scam_triage import lexicons
from scam_triage.model import TriageModel
from scam_triage.signals import detect
from scam_triage.taxonomy import LEGIT, get_scam_type

MAX_REASONS = 4
MAX_PHRASES = 5

# Context signals describe *what* a message is about; on their own they are not
# suspicious, so they are listed after behavioural signals and hidden on low risk.
CONTEXT_SIGNALS = {"has_link", "money_amount", "payment_rail", "delivery", "bank_mention"}

# Safety net: what a message *asks you to do*, independent of how scammy it sounds.
ASK_SIGNALS = {
    "money": ("money_request", "fee_to_unlock", "safe_account"),
    "code": ("code_request", "credential_request"),
    "app": ("remote_access",),
}

# Conversation context: the latest message is also scored together with the ones before it.
THREAD_MAX_MESSAGES = 8
THREAD_MAX_CHARS = 2000
LEVEL_RANK = {"low": 0, "medium": 1, "high": 2}

# Message headers in text copied from WhatsApp, e.g. "[04/10/2026, 09:41] Mum: ..." (iOS),
# "[09:41, 04/10/2026] Mum: ..." (Android) or "04/10/2026, 09:41 - Mum: ..." (chat export).
_DATE = r"\d{1,4}[/.-]\d{1,2}[/.-]\d{1,4}"
_TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?"
CONVERSATION_HEADER = (
    rf"^\s*(?:\[(?:{_DATE},? {_TIME}|{_TIME},? {_DATE})\]|{_DATE},? {_TIME} -)\s*[^:\n]{{1,60}}:\s?"
)
_HEADER_RE = re.compile(CONVERSATION_HEADER)


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
    asks: list[str] = field(default_factory=list)  # "money" | "code" | "app"
    cautions: list[str] = field(default_factory=list)  # safety-net notes, only when risk is low
    thread_size: int = 1  # messages considered
    from_context: bool = False  # True when the conversation, not the latest message alone, raised the level

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
    asks = asks_in(text, lang)

    if level == "low":
        phrases = []
        shown = get_scam_type(LEGIT, lang)
        summary = "No strong scam patterns found."
        if reasons:
            summary += " A few things are worth double-checking, though."
        return TriageResult(round(score, 4), level, LEGIT, shown.label, round(1 - score, 4), summary,
                            reasons, phrases, shown.next_steps, lang, model.meta.get("version", "?"),
                            asks, cautions_for(asks, lang))

    st = get_scam_type(type_id, lang)
    lead = "This looks like a scam" if level == "high" else "This could be a scam"
    summary = f"{lead}: {st.label.lower()}. {st.description}"
    return TriageResult(round(score, 4), level, type_id, st.label, round(type_conf, 4), summary,
                        reasons, phrases, st.next_steps, lang, model.meta.get("version", "?"), asks, [])


def asks_in(text: str, lang: str = "en") -> list[str]:
    """What the message asks the reader to do (money, code, app), from every signal that fired."""
    fired = {h.id for h in detect(text, lang)}
    return [ask for ask, sids in ASK_SIGNALS.items() if fired.intersection(sids)]


def cautions_for(asks: list[str], lang: str = "en") -> list[str]:
    texts = lexicons.load(lang).CAUTIONS
    return [texts[a] for a in asks]


def thread_window(messages: list[str]) -> list[str]:
    """The most recent non-empty messages, at most THREAD_MAX_MESSAGES and THREAD_MAX_CHARS in total."""
    msgs = [m.strip() for m in messages if m and m.strip()][-THREAD_MAX_MESSAGES:]
    while len(msgs) > 1 and len("\n".join(msgs)) > THREAD_MAX_CHARS:
        msgs = msgs[1:]
    return msgs


def triage_thread(messages: list[str], lang: str = "en", model: TriageModel | None = None) -> TriageResult:
    """Judge the latest message in the light of the conversation so far (oldest first).

    The latest message is scored alone and together with the messages before it; the riskier
    verdict wins. This catches slow-burn scams whose danger builds over several harmless-looking
    messages. The safety net looks at what any message in the window asks for.
    """
    msgs = thread_window(messages)
    if not msgs:
        raise ValueError("no messages")
    latest = triage(msgs[-1], lang, model)
    if len(msgs) == 1:
        return latest
    whole = triage("\n".join(msgs), lang, model)
    if LEVEL_RANK[whole.risk_level] > LEVEL_RANK[latest.risk_level]:
        lead = "Taken together, these messages look like a scam" if whole.risk_level == "high" \
            else "Taken together, these messages could be a scam"
        st = get_scam_type(whole.scam_type, lang)
        whole.summary = f"{lead}: {st.label.lower()}. {st.description}"
        whole.thread_size, whole.from_context = len(msgs), True
        return whole
    latest.thread_size = len(msgs)
    latest.asks = whole.asks  # requests made earlier in the conversation still count
    latest.cautions = cautions_for(whole.asks, lang) if latest.risk_level == "low" else []
    return latest


def split_conversation(text: str) -> list[str]:
    """Split text copied from a WhatsApp chat into messages (oldest first); otherwise [text]."""
    messages: list[str] = []
    headers = 0
    for line in text.splitlines():
        m = _HEADER_RE.match(line)
        if m:
            headers += 1
            messages.append(line[m.end():])
        elif messages:
            messages[-1] += "\n" + line
        else:
            messages.append(line)
    if headers < 2:
        return [text]
    return [m.strip() for m in messages if m.strip()]


def triage_text(text: str, lang: str = "en", model: TriageModel | None = None) -> TriageResult:
    """One message, or a pasted conversation (several WhatsApp messages) judged as a whole."""
    messages = split_conversation(text)
    return triage_thread(messages, lang, model) if len(messages) > 1 else triage(text, lang, model)


def _is_readable_phrase(feature: str) -> bool:
    if feature.startswith(("char:", "signal:")) or "__" in feature:
        return False
    words = feature.split()
    return not all(w in ENGLISH_STOP_WORDS or w.startswith("__") or w.isdigit() or len(w) < 3 for w in words)
