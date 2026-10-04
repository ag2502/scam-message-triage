"""Export the model in a compact format for the native apps, plus a golden file for parity tests.

    python scripts/export_mobile.py   # -> mobile/shared/model/{model.json,vocab_word.txt,vocab_char.txt,weights.bin}
                                       #    mobile/shared/golden/golden.jsonl

weights.bin layout (little-endian, no header; sizes are in model.json):
    float64[n_word]           word idf
    float64[n_char]           char idf
    float64[n_feat]           risk coefficients (n_feat = n_word + n_char + n_signals)
    float32[n_classes*n_feat] type coefficients, row-major by class
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from export_web import export_model  # noqa: E402

from scam_triage.dataset import DATA_DIR, load_split, read_jsonl  # noqa: E402
from scam_triage.model import TriageModel  # noqa: E402
from scam_triage.signals import detect  # noqa: E402
from scam_triage.reply import format_reply  # noqa: E402
from scam_triage.triage import split_conversation, triage, triage_thread  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mobile" / "shared"

EDGE_CASES = [
    "Hi mãe 😩😩 it's João, novo número. Can you send R$1.200 by Pix? urgent!!",
    "Itaú: Pix received R$85,00 from Marina Costa.",
    "Do not share this code with anyone. We will never ask you to move your money to a safe account.",
    "visit https://user@usps.com-track.top:8080/x?y=1 now",
    "Paytm: ₹1,200 paid to Reliance Fresh. UPI Ref 4209118823.",
    "ＵＲＧＥＮＴ​ pay ｎｏｗ at bit.ly/abc",
    "ok",
]


def golden_texts() -> list[str]:
    texts = list(EDGE_CASES)
    for path in sorted((DATA_DIR / "en").glob("challenge*.jsonl")):
        texts += [r["text"] for r in read_jsonl(path)]
    texts += [r["text"] for r in load_split("test")[::7]]
    return texts


def main() -> None:
    lang = "en"
    m = TriageModel.load(lang=lang)
    meta = export_model(lang)
    words, chars = meta["word"].pop("vocab"), meta["char"].pop("vocab")
    meta["word"].pop("idf"); meta["char"].pop("idf")
    meta["risk"].pop("coef")
    for k in ("index", "coef"):
        meta["type"].pop(k)
    n_feat = len(words) + len(chars) + len(meta["signal_ids"])
    meta["sizes"] = {"n_word": len(words), "n_char": len(chars), "n_signals": len(meta["signal_ids"]),
                     "n_feat": n_feat, "n_classes": len(meta["type"]["classes"])}
    assert all("\n" not in t for t in words + chars)

    model_dir = OUT / "model"
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "model.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    (model_dir / "vocab_word.txt").write_text("\n".join(words) + "\n", encoding="utf-8")
    (model_dir / "vocab_char.txt").write_text("\n".join(chars) + "\n", encoding="utf-8")
    f = m.featurizer
    blob = b"".join([
        f.word.idf_.astype("<f8").tobytes(),
        f.char.idf_.astype("<f8").tobytes(),
        m.risk_clf.coef_[0].astype("<f8").tobytes(),
        m.type_clf.coef_.astype("<f4").tobytes(),
    ])
    (model_dir / "weights.bin").write_bytes(blob)
    assert len(blob) == 8 * (len(words) + len(chars) + n_feat) + 4 * meta["sizes"]["n_classes"] * n_feat

    (OUT / "golden").mkdir(parents=True, exist_ok=True)
    with (OUT / "golden" / "golden.jsonl").open("w", encoding="utf-8") as g:
        for text in golden_texts():
            res = triage(text)
            r = res.to_dict()
            g.write(json.dumps({
                "text": text,
                "risk_score": r["risk_score"], "risk_level": r["risk_level"], "scam_type": str(r["scam_type"]),
                "reasons": r["reasons"], "key_phrases": r["key_phrases"],
                "signals": [[h.id, h.evidence] for h in detect(text)],
                "asks": r["asks"], "cautions": r["cautions"], "reply": format_reply(res),
            }, ensure_ascii=False) + "\n")

    # Conversations: every prefix of every blind test conversation (what a phone sees as messages arrive).
    with (OUT / "golden" / "threads.jsonl").open("w", encoding="utf-8") as g:
        for conv in read_jsonl(DATA_DIR / "en" / "threads.jsonl"):
            for i in range(1, len(conv["messages"]) + 1):
                msgs = conv["messages"][:i]
                res = triage_thread(msgs)
                g.write(json.dumps({
                    "messages": msgs, "risk_score": res.risk_score, "risk_level": res.risk_level,
                    "scam_type": str(res.scam_type), "reasons": res.reasons, "key_phrases": res.key_phrases,
                    "asks": res.asks, "cautions": res.cautions, "thread_size": res.thread_size,
                    "from_context": res.from_context, "summary": res.summary, "reply": format_reply(res),
                }, ensure_ascii=False) + "\n")

    # Splitting text copied from WhatsApp into messages.
    split_cases = [
        "[04/10/2026, 09:41:12] Mum: Hi it's me\n[04/10/2026, 09:42:03] Mum: new number\nsave it",
        "[09:41, 04/10/2026] Mum: Hi it's me\n[09:42, 04/10/2026] Mum: new number",
        "04/10/2026, 09:41 - Mum: Hi it's me\n04/10/2026, 09:42 - Mum: new number",
        "[10/4/26, 9:41 PM] Lia Souza: oi!\n[10/4/26, 9:43 PM] Lia Souza: tudo bem?",
        "Just one message\nwith two lines",
        "[04/10/2026, 09:41] Mum: only one header",
        "Intro line\n[04/10/2026, 09:41] A: one\n\n[04/10/2026, 09:42] B: two 😩",
    ]
    with (OUT / "golden" / "split.jsonl").open("w", encoding="utf-8") as g:
        for text in split_cases:
            g.write(json.dumps({"text": text, "messages": split_conversation(text)}, ensure_ascii=False) + "\n")

    size = sum(p.stat().st_size for p in model_dir.iterdir())
    print(f"wrote {model_dir.relative_to(ROOT)} ({size / 1024:.0f} KB) and golden.jsonl ({len(golden_texts())} cases)")


if __name__ == "__main__":
    main()
