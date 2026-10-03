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
    if r.reasons:
        lines += ["", "*Why:*", *(f"• {reason}" for reason in r.reasons)]
    if r.next_steps:
        lines += ["", "*What to do:*", *(f"• {step}" for step in r.next_steps)]
    lines += ["", "_Automated check. It can be wrong. When in doubt, verify through a channel you already trust._"]
    return "\n".join(lines)
