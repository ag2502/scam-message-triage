"""Scam types the triage model can output, with plain-language guidance.

The taxonomy is payment-rail agnostic: "fake payment receipt" covers a forged
Pix comprovante, a fake Zelle/UPI confirmation or a doctored bank-transfer
screenshot alike. Guidance text is per language so new locales can be added
without touching the model.
"""

from __future__ import annotations

from dataclasses import dataclass, field

LEGIT = "legit"


@dataclass(frozen=True)
class ScamType:
    id: str
    label: str
    description: str
    next_steps: list[str] = field(default_factory=list)


_EN: dict[str, ScamType] = {
    t.id: t
    for t in [
        ScamType(
            "family_impersonation",
            "Fake relative or friend",
            "Someone claims to be a family member or friend on a new number and asks for money urgently.",
            [
                "Do not send money yet.",
                "Call the person on the number you already have saved, or ask a question only they could answer.",
                "If you can't reach them, check with another family member first.",
            ],
        ),
        ScamType(
            "fake_payment_receipt",
            "Fake payment receipt / overpayment",
            "Claims money was sent to you (often 'by mistake') and asks you to return it, usually with a forged receipt.",
            [
                "Open your banking app directly and check your real balance. Ignore screenshots and receipts.",
                "Do not 'refund' anything until the money is actually in your account and has cleared.",
                "If a mistaken payment is real, your bank can reverse it; you don't need to send anything.",
            ],
        ),
        ScamType(
            "bank_impersonation",
            "Fake bank agent",
            "Pretends to be your bank's fraud team and pushes you to call a number, share codes or move money to a 'safe account'.",
            [
                "Hang up or stop replying. Your bank will never ask you to move money to a 'safe account'.",
                "Call your bank using the number on the back of your card or in the official app.",
                "Never share one-time codes, PINs or passwords, and never install remote-access apps on request.",
            ],
        ),
        ScamType(
            "delivery_fee",
            "Fake delivery / parcel fee",
            "Says a parcel is held and asks for a small fee or address confirmation through a link.",
            [
                "Do not click the link or pay the fee.",
                "Track parcels only through the courier's official app or the shop you ordered from.",
            ],
        ),
        ScamType(
            "toll_fine_tax",
            "Fake fine, toll or tax notice",
            "Impersonates a government agency, toll operator or tax office demanding payment of an unpaid fine or refund claim.",
            [
                "Do not pay through the link in the message.",
                "Log in to the official government or toll website yourself (type the address) to check for real notices.",
            ],
        ),
        ScamType(
            "account_phishing",
            "Account suspension / login phishing",
            "Warns that an account (bank, streaming, email, social) is locked and asks you to 'verify' through a link.",
            [
                "Do not click the link or enter your password.",
                "Open the service's official app or website directly to check your account status.",
                "If you already entered details, change your password now and turn on two-factor authentication.",
            ],
        ),
        ScamType(
            "verification_code_theft",
            "Verification code theft",
            "Asks you to forward a code that was 'sent by mistake'. This code lets them take over your WhatsApp, bank or email.",
            [
                "Never share a verification or one-time code with anyone, even a friend.",
                "If you already shared it, turn on two-step verification in the affected app immediately.",
            ],
        ),
        ScamType(
            "prize_lottery",
            "Fake prize / giveaway",
            "Says you won a prize, lottery or giveaway and must pay a fee or share details to claim it.",
            [
                "You can't win a contest you didn't enter. Real prizes never require a fee.",
                "Do not pay, click or share personal details.",
            ],
        ),
        ScamType(
            "job_task",
            "Fake job / task scam",
            "Offers easy money for simple online tasks (liking videos, reviews), then asks you to deposit money to 'unlock' earnings.",
            [
                "Legitimate employers never ask you to pay to work or to unlock wages.",
                "Stop depositing money; earlier small 'payouts' are bait.",
            ],
        ),
        ScamType(
            "investment_crypto",
            "Investment / crypto scam",
            "Promises guaranteed or unrealistically high returns, often in crypto or via a 'mentor' or trading group.",
            [
                "Guaranteed high returns are a hallmark of fraud.",
                "Check the firm with your country's financial regulator before investing anything.",
            ],
        ),
    ]
}

_EN_LEGIT = ScamType(
    LEGIT,
    "Probably legitimate",
    "No strong scam patterns found.",
    [
        "Stay careful: if the message asks for money or codes, confirm through a channel you already trust.",
    ],
)

_REGISTRY: dict[str, dict[str, ScamType]] = {"en": {**_EN, LEGIT: _EN_LEGIT}}

SCAM_TYPE_IDS: list[str] = list(_EN)
ALL_LABELS: list[str] = [LEGIT, *SCAM_TYPE_IDS]


def get_scam_type(type_id: str, lang: str = "en") -> ScamType:
    return _REGISTRY.get(lang, _REGISTRY["en"])[type_id]
