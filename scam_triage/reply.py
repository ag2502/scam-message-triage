"""Human-readable verdicts for chat (WhatsApp) and the terminal."""

from __future__ import annotations

from scam_triage.triage import TriageResult

_BADGE = {"high": "🔴 HIGH RISK", "medium": "🟠 MEDIUM RISK", "low": "🟢 LOW RISK"}


def format_reply(r: TriageResult) -> str:
    """Plain text with WhatsApp-style *bold*; also reads fine in a terminal."""
    lines = [f"{_BADGE[r.risk_level]} ({r.risk_score:.0%})", ""]
    if r.risk_level == "low":
        lines.append(f"*{r.scam_type_label}.* {r.summary}")
    else:
        lines.append(f"*Likely scam type:* {r.scam_type_label}")
        lines.append(r.summary.split(". ", 1)[-1])
    if r.from_context:
        lines.append(f"_Based on the last {r.thread_size} messages together._")
    if r.reasons:
        lines += ["", "*Why:*", *(f"• {reason}" for reason in r.reasons)]
    if r.cautions:
        lines += ["", "*Before you act:*", *(f"• {c}" for c in r.cautions)]
    if r.next_steps:
        lines += ["", "*What to do:*", *(f"• {step}" for step in r.next_steps)]
    lines += ["", "_Automated check. It can be wrong. When in doubt, verify through a channel you already trust._"]
    return "\n".join(lines)
