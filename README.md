# Scam-Message Triage

Forward a suspicious message and get back a **risk score**, the **scam type** and **what to do next**, with a
plain-language reason.

Instant-payment systems (Pix in Brazil, UPI in India, SPEI in Mexico, Zelle in the US, Faster Payments in the UK)
settle in seconds and are hard to reverse. Scammers exploit this with urgent WhatsApp/SMS messages: a "relative" on a
new number, a forged payment receipt, a fake bank agent. People have no quick check before they pay. This project is
that check: an explainable classifier, a WhatsApp bot and an HTTP API.

The engine is **rail-agnostic** and **language-pluggable**. English ships first; PT-BR and ES are next.

```
$ scam-triage "Hi mum, I dropped my phone, this is my new number. Can you send R\$800 by Pix? Urgent, can't talk"
🔴 HIGH RISK (100%)

*Likely scam type:* Fake relative or friend
Someone claims to be a family member or friend on a new number and asks for money urgently.

*Why:*
• Claims to be someone you know writing from a new or temporary number.
• Pressures you to act fast. Scammers rush you so you don't stop to check.
• Claims to be a family member without any way to verify it.
• Asks you to send or pay money.

*What to do:*
• Do not send money yet.
• Call the person on the number you already have saved, or ask a question only they could answer.
• If you can't reach them, check with another family member first.
```

## How it works

```
message ─► normalize ─┬─► signals (regex lexicon, URL/phone/amount checks) ──┐
                      └─► word + char n-gram TF-IDF ─────────────────────────┤
                                                                             ▼
                          risk model (binary logistic) ──► score ──► low / medium / high
                          type model (multinomial logistic) ──► scam type
                                                                             ▼
             reasons = signals that fired AND push toward "scam"  +  next steps for the type
```

- **Signals** ([scam_triage/signals.py](scam_triage/signals.py), [lexicons/en.py](scam_triage/lexicons/en.py)):
  human-readable patterns such as "asks you to share a one-time code", "move money to a safe account", "new number",
  "fee to unlock", plus look-alike/shortened/risky-TLD links. Negations ("**do not** share this code") are respected.
- **Model** ([scam_triage/model.py](scam_triage/model.py)): linear models, so every verdict decomposes into the
  signals and phrases that drove it. URLs, phones, amounts and digits are masked so the model learns patterns rather
  than values.
- **Thresholds**: *high* and *medium* are set at 1% and 5% false-positive rate, using template-grouped out-of-fold
  scores, so the levels are calibrated on phrasings the model hasn't seen.
- **Taxonomy** ([scam_triage/taxonomy.py](scam_triage/taxonomy.py)): 10 scam types with descriptions and next steps:
  fake relative, fake payment receipt, fake bank agent, delivery fee, fine/toll/tax, account phishing, verification
  code theft, prize, job/task, investment/crypto.

## Results (EN, v0.3)

Full report: [reports/en/EVALUATION.md](reports/en/EVALUATION.md). Thresholds are fixed at training time and never
tuned on the evaluation data.

| Evaluation set | ROC-AUC | *High* level: recall / FPR | *Medium* level: recall / FPR | Type macro-F1 |
|---|---|---|---|---|
| **Blind hand-written challenge v3** (30 scam / 30 legit) | 0.984 | 86.7% / 0.0% (0 of 30) | 93.3% / 3.3% (1 of 30) | 0.87 |
| Held-out templates + real UCI ham (665 / 1,505) | 0.989 | 85.9% / 2.7% | 93.1% / 4.0% | 0.69 |
| Template-grouped 5-fold CV | 0.985 ± 0.012 | recall @ 1% FPR: 89.6% ± 9.6% | | 0.73 ± 0.06 |

**What these numbers mean:**
- Precision depends on how many forwarded messages are actually scams. On the held-out test set, the *high* level
  gives 93% precision. Re-weighted to 10% scam prevalence it would be 78%, and at 1% prevalence 25%. A checker that
  people forward *suspicious* messages to should see a high prevalence. The bot's wording ("can be wrong, verify
  through a channel you trust") reflects the remaining risk.
- The *high* threshold targets 1% FPR but lands at 2.7% on held-out templates: 32 of the 40 false positives come from
  one legitimate template (outgoing bank-transfer confirmations) and the other 8 from a second one. Real UCI
  messages had 0.0% false positives at *high*.
- Known misses: relationship-starter scams ("sorry, wrong number… do you invest?") and some cash-courier scripts.
  Single-message triage can't see where a conversation is heading.
- Training data is synthetic. Each challenge set was committed **before** the changes it evaluates, so the git
  history shows it wasn't tuned on. See the [dataset card](data/en/DATASET_CARD.md).

## Quickstart

```bash
uv venv && source .venv/bin/activate      # or: python -m venv .venv
uv pip install -e ".[dev]"                # or: pip install -e ".[dev]"

scam-triage "Your E-ZPass balance of \$4.15 is overdue, pay at ezpass-tolls.vip/pay"
scam-triage --json "..."                  # full structured result

uvicorn scam_triage.api:app --reload      # http://127.0.0.1:8000/docs
curl -s localhost:8000/v1/triage -H 'Content-Type: application/json' \
     -d '{"text": "Hi, I sent you R$500 by Pix by mistake, can you send it back?"}'
```

`POST /v1/triage` returns `risk_score`, `risk_level`, `scam_type`, `scam_type_label`, `type_confidence`, `summary`,
`reasons`, `key_phrases`, `next_steps`, `model_version` and a ready-to-send `reply_text`.

### Rebuild data, retrain, evaluate

```bash
python scripts/build_dataset.py   # synthetic corpus + downloads UCI ham into data/external/
python scripts/train.py           # -> models/en/triage.joblib (~15 s on a laptop)
python scripts/evaluate.py        # -> reports/en/eval.json + EVALUATION.md
pytest
```

## WhatsApp bot

The webhook lives in [scam_triage/whatsapp.py](scam_triage/whatsapp.py) and is mounted on the same FastAPI app.

1. Create a Meta app with the **WhatsApp** product and note the test phone number, the **app secret** and a
   **system-user access token** with `whatsapp_business_messaging`.
2. Copy `.env.example` to `.env`, fill it in and export it (`set -a; source .env; set +a`).
3. Run the API somewhere reachable over HTTPS (for local testing: `uvicorn scam_triage.api:app --port 8000` plus a
   tunnel such as `cloudflared tunnel --url http://localhost:8000`).
4. In the Meta dashboard, set the webhook URL to `https://<host>/webhooks/whatsapp`, set the verify token to your
   `WHATSAPP_VERIFY_TOKEN`, and subscribe to the `messages` field.
5. Forward any message to the number. The bot replies to it with the verdict.

Every POST is verified with `X-Hub-Signature-256`. Meta's retries are de-duplicated. Images and voice notes get a
"please paste the text" reply. Message text is never logged.

## Adding a language

1. `scam_triage/lexicons/<lang>.py`: `PATTERNS`, `REASONS`, `IMITATED_BRANDS`, `LURE_WORDS`, and add the code to
   `SUPPORTED_LANGS`.
2. `scam_triage/synth/<lang>.py`: `SLOTS` and `TEMPLATES` with the same labels.
3. Add the language to the taxonomy registry in `taxonomy.py` (labels, descriptions, next steps).
4. Write a blind challenge set **before** training, then build, train and evaluate with `--lang <lang>`.

## Project layout

```
scam_triage/        taxonomy, signals, lexicons/, synth/, dataset, model, triage, evaluate, api, whatsapp, cli
scripts/            build_dataset.py, train.py, evaluate.py
data/en/            synthetic splits, challenge sets, DATASET_CARD.md
models/en/          trained model (joblib)
reports/en/         eval.json, EVALUATION.md
tests/              pytest suite
```

## Roadmap

- PT-BR lexicon, templates and challenge set (Pix, boleto, "falsa central", "golpe do novo número"); then ES (SPEI, Bre-B).
- Collect consented, labelled forwards from the bot to replace synthetic test data.
- Optional transformer head (BERTimbau / multilingual small model) behind the same `triage()` interface, kept only if
  it beats the linear model at low FPR.
- OCR for screenshots of messages and forged payment receipts.

## Disclaimer

This is an automated aid, not financial or legal advice. It can miss scams and can flag legitimate messages. Always
verify through a channel you already trust: the number saved in your phone, or the official app or website you type
in yourself.

## License

Code: MIT. Synthetic and hand-written data: CC BY 4.0. UCI SMS Spam Collection: CC BY 4.0 (Almeida & Gómez Hidalgo),
downloaded on demand and not redistributed.
