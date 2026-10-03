"""Explainable scam signals.

Each signal is a binary, human-readable pattern (e.g. "asks you to share a
one-time code"). Signals are used twice: as features for the classifier, and as
the plain-language reasons returned to the user.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse

from scam_triage import lexicons

_ZERO_WIDTH = dict.fromkeys(map(ord, "​‌‍⁠﻿"), None)

URL_RE = re.compile(
    r"(?:https?://|www\.)[^\s<>\"']+|\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.(?:com|net|org|info|top|xyz|icu|click|live|shop|buzz|site|online|vip|cc|io|me|ly|gd|co|link|app|support|help|services?|delivery)(?:/[^\s]*)?\b",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)")
AMOUNT_RE = re.compile(
    r"(?:r\$|us\$|\$|£|€|₹|rs\.?|inr|usd|brl|mxn|cop|gbp|eur)\s?\d[\d.,]*|\d[\d.,]*\s?(?:dollars|pounds|euros|reais|rupees|pesos|usd|brl|gbp|eur|inr)\b",
    re.IGNORECASE,
)

URL_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "rb.gy", "goo.gl", "ow.ly", "shorturl.at",
    "tiny.cc", "s.id", "rebrand.ly", "t.ly", "buff.ly",
}
RISKY_TLDS = {
    "top", "xyz", "icu", "click", "live", "shop", "buzz", "site", "online", "vip", "cc", "link",
    "support", "help", "services", "service", "delivery", "info", "rest", "cyou", "sbs", "cfd",
}

LINK_SIGNALS = ("has_link", "suspicious_link", "has_phone_number", "money_amount")


def normalize(text: str) -> str:
    """NFKC-normalize, drop zero-width characters, unify quotes, collapse whitespace."""
    text = unicodedata.normalize("NFKC", text).translate(_ZERO_WIDTH)
    text = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def extract_urls(text: str) -> list[str]:
    return [m.group(0).rstrip(".,;:!?)") for m in URL_RE.finditer(text)]


def _host(url: str) -> str:
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "http://" + url
    return (urlparse(url).hostname or "").lower()


def is_suspicious_url(url: str, imitated_brands: list[str]) -> bool:
    host = _host(url)
    if not host:
        return False
    if host in URL_SHORTENERS:
        return True
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", host):
        return True
    labels = host.split(".")
    if labels[-1] in RISKY_TLDS:
        return True
    registrable = labels[-2] if len(labels) >= 2 else host
    # Brand + extra words in the registrable label ("usps-redelivery", "paypal-secure-login").
    if "-" in registrable and any(b in registrable for b in imitated_brands):
        return True
    # Many subdomains stacked in front of an unrelated domain ("chase.com.verify-acct.net").
    if len(labels) >= 4 and any(b in ".".join(labels[:-2]) for b in imitated_brands):
        return True
    return False


@dataclass(frozen=True)
class SignalHit:
    id: str
    reason: str
    evidence: str


@lru_cache(maxsize=None)
def _compiled(lang: str) -> dict[str, list[re.Pattern[str]]]:
    lex = lexicons.load(lang)
    return {sid: [re.compile(p, re.IGNORECASE) for p in pats] for sid, pats in lex.PATTERNS.items()}


@lru_cache(maxsize=None)
def signal_ids(lang: str = "en") -> tuple[str, ...]:
    return (*_compiled(lang), *LINK_SIGNALS)


def detect(text: str, lang: str = "en") -> list[SignalHit]:
    """Return every signal that fires on `text`, with the matching snippet as evidence."""
    lex = lexicons.load(lang)
    norm = normalize(text)
    hits: list[SignalHit] = []
    for sid, patterns in _compiled(lang).items():
        for pat in patterns:
            m = pat.search(norm)
            if m:
                hits.append(SignalHit(sid, lex.REASONS[sid], m.group(0)))
                break

    urls = extract_urls(norm)
    if urls:
        hits.append(SignalHit("has_link", lex.REASONS["has_link"], urls[0]))
        bad = [u for u in urls if is_suspicious_url(u, lex.IMITATED_BRANDS)]
        if bad:
            hits.append(SignalHit("suspicious_link", lex.REASONS["suspicious_link"], bad[0]))
    phone = PHONE_RE.search(norm)
    if phone and sum(c.isdigit() for c in phone.group(0)) >= 9:
        hits.append(SignalHit("has_phone_number", lex.REASONS["has_phone_number"], phone.group(0).strip()))
    amount = AMOUNT_RE.search(norm)
    if amount:
        hits.append(SignalHit("money_amount", lex.REASONS["money_amount"], amount.group(0)))
    return hits


def signal_vector(text: str, lang: str = "en") -> list[int]:
    """Binary vector over `signal_ids(lang)`, for use as model features."""
    fired = {h.id for h in detect(text, lang)}
    return [int(sid in fired) for sid in signal_ids(lang)]
