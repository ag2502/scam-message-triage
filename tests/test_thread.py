from scam_triage.reply import format_reply
from scam_triage.triage import (THREAD_MAX_MESSAGES, split_conversation, thread_window, triage, triage_text,
                                triage_thread)

SLOW_BURN = [
    "Hi, is this David? Oh sorry, wrong number!",
    "No worries 😊 Nice to meet you anyway. Where are you based?",
    "My uncle taught me to trade gold futures with an AI system, I made 38% last month",
    "You should try it, the platform is very safe. Start small with $300 and I will guide you",
]


def test_safety_net_on_low_risk_requests():
    r = triage("Can you lend me $20 till payday? I'll pay you back Friday")
    assert r.risk_level == "low" and r.asks == ["money"] and r.cautions
    assert "*Before you act:*" in format_reply(r)
    otp = triage("Your WhatsApp code: 482-019. Don't share this code with others.")
    assert otp.asks == [] and otp.cautions == []


def test_no_caution_when_already_flagged():
    r = triage("Hi Mum, new number! Send £500 by bank transfer now, can't talk")
    assert r.risk_level == "high" and "money" in r.asks and r.cautions == []


def test_conversation_raises_a_slow_burn_scam():
    alone = triage(SLOW_BURN[-1])
    together = triage_thread(SLOW_BURN)
    assert alone.risk_level == "low"
    assert together.risk_level in {"medium", "high"} and together.from_context
    assert together.thread_size == len(SLOW_BURN) and together.summary.startswith("Taken together")
    assert "_Based on the last 4 messages together._" in format_reply(together)


def test_conversation_never_lowers_the_latest_verdict():
    msgs = ["Hey, how are you?", "Royal Mail: your parcel is on hold, pay the £1.99 fee at royalmail-redelivery.top"]
    assert triage_thread(msgs).risk_level == triage(msgs[-1]).risk_level == "high"


def test_window_limits():
    msgs = [f"message number {i} about the weekend" for i in range(20)]
    assert len(thread_window(msgs)) == THREAD_MAX_MESSAGES
    assert thread_window(["x" * 1500, "y" * 1500]) == ["y" * 1500]


def test_split_whatsapp_formats():
    ios = "[04/10/2026, 09:41:12] Mum: Hi it's me\n[04/10/2026, 09:42:03] Mum: new number\nsave it"
    android = "[09:41, 04/10/2026] Mum: Hi it's me\n[09:42, 04/10/2026] Mum: new number"
    export = "04/10/2026, 09:41 - Mum: Hi it's me\n04/10/2026, 09:42 - Mum: new number"
    assert split_conversation(ios) == ["Hi it's me", "new number\nsave it"]
    assert split_conversation(android) == ["Hi it's me", "new number"]
    assert split_conversation(export) == ["Hi it's me", "new number"]
    assert split_conversation("Just one message\nwith two lines") == ["Just one message\nwith two lines"]


def test_triage_text_uses_the_conversation():
    pasted = "\n".join(f"[04/10/2026, 09:4{i}] Lia: {m}" for i, m in enumerate(SLOW_BURN))
    assert triage_text(pasted).from_context
