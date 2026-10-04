"""Replay conversations message by message and compare single-message vs conversation-aware triage.

    python scripts/evaluate_threads.py   # -> reports/en/threads.json + THREADS.md

A conversation counts as warned at a level if any step reaches it, the way a phone would alert
when that message arrives. Uses data/en/threads.jsonl (written before the feature existed).
"""

from __future__ import annotations

import json

from scam_triage.dataset import DATA_DIR, ROOT, read_jsonl
from scam_triage.triage import LEVEL_RANK, triage, triage_thread


def replay(messages: list[str]) -> dict:
    single = [triage(m).risk_level for m in messages]
    thread = [triage_thread(messages[: i + 1]).risk_level for i in range(len(messages))]
    cautions = [bool(triage_thread(messages[: i + 1]).cautions) for i in range(len(messages))]
    return {"single": single, "thread": thread, "caution": cautions}


def first_at(levels: list[str], level: str) -> int | None:
    return next((i + 1 for i, lv in enumerate(levels) if LEVEL_RANK[lv] >= LEVEL_RANK[level]), None)


def main() -> None:
    rows = read_jsonl(DATA_DIR / "en" / "threads.jsonl")
    out = []
    for r in rows:
        rep = replay(r["messages"])
        out.append({"id": r["id"], "label": r["label"], "is_scam": r["is_scam"], "n": len(r["messages"]), **rep})

    def summary(mode: str, level: str) -> dict:
        scams = [o for o in out if o["is_scam"]]
        legit = [o for o in out if not o["is_scam"]]
        caught = [first_at(o[mode], level) for o in scams]
        return {
            "scam_threads_warned": sum(c is not None for c in caught), "scam_threads": len(scams),
            "legit_threads_warned": sum(first_at(o[mode], level) is not None for o in legit), "legit_threads": len(legit),
            "avg_messages_before_warning": round(sum(c for c in caught if c) / max(1, sum(c is not None for c in caught)), 2),
        }

    report = {mode: {lv: summary(mode, lv) for lv in ("medium", "high")} for mode in ("single", "thread")}
    legit_money = [o for o in out if not o["is_scam"] and any(o["caution"])]
    report["legit_threads_with_caution"] = len(legit_money)
    report["scam_threads_low_but_cautioned"] = sum(
        1 for o in out if o["is_scam"] and first_at(o["thread"], "medium") is None and any(o["caution"]))
    report["threads"] = out
    d = ROOT / "reports" / "en"
    (d / "threads.json").write_text(json.dumps(report, indent=2))

    def line(mode: str, lv: str) -> str:
        s = report[mode][lv]
        return (f"| {mode} | {lv} | {s['scam_threads_warned']}/{s['scam_threads']} | {s['avg_messages_before_warning']} | "
                f"{s['legit_threads_warned']}/{s['legit_threads']} |")
    missed = [o for o in out if o["is_scam"] and first_at(o["thread"], "medium") is None]
    md = f"""# Conversations: single message vs conversation-aware

Replays the 32 hand-written conversations in `data/en/threads.jsonl` (16 slow-burn scams, 16 normal chats,
committed before this feature was written) one incoming message at a time. A conversation is *warned* if any
message reaches the level.

| Mode | Level | Scam conversations warned | Avg. message of first warning | Normal conversations warned |
|---|---|---|---|---|
{line("single", "medium")}
{line("single", "high")}
{line("thread", "medium")}
{line("thread", "high")}

Safety net: {report["legit_threads_with_caution"]} of 16 normal conversations get a "verify before paying / never share
codes" caution (they ask for money or codes, so that is intended), and {report["scam_threads_low_but_cautioned"]} scam
conversations that are never warned still get that caution.

Still missed in conversation mode (never reach medium): {", ".join(o["id"] for o in missed) or "none"}.

Caveat: 32 conversations written by the same author as the templates. Directionally useful, not a benchmark.
"""
    (d / "THREADS.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
