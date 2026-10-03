import re

from scam_triage.synth import generate
from scam_triage.taxonomy import ALL_LABELS


def test_generate_is_deterministic_and_complete():
    a = generate(seed=3, scam_per_label=24, legit_total=120)
    b = generate(seed=3, scam_per_label=24, legit_total=120)
    assert [r["text"] for r in a] == [r["text"] for r in b]
    assert {r["label"] for r in a} == set(ALL_LABELS)
    assert not any("{" in r["text"] for r in a), "unfilled slot"


def test_templates_do_not_leak_across_splits():
    rows = generate(seed=3, scam_per_label=24, legit_total=120)
    split_of: dict[str, set[str]] = {}
    for r in rows:
        split_of.setdefault(r["template_id"], set()).add(r["split"])
    assert all(len(s) == 1 for s in split_of.values())
    for label in ALL_LABELS:
        splits = {r["split"] for r in rows if r["label"] == label}
        assert splits == {"train", "val", "test"}


def test_one_currency_per_message():
    # Alternation order matters: "R$" and "MXN $" must win over a bare "$".
    currency = re.compile(r"R\$|MXN \$|\$|£|€|₹|dollars|pounds|euros|reais|rupees|pesos", re.IGNORECASE)
    word_to_symbol = {"dollars": "$", "pounds": "£", "euros": "€", "reais": "R$", "rupees": "₹", "pesos": "MXN $"}
    for r in generate(seed=5, scam_per_label=60, legit_total=60):
        found = {word_to_symbol.get(m.lower(), m.upper()) for m in currency.findall(r["text"])}
        assert len(found) <= 1, r["text"]
