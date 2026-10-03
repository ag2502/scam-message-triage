# Dataset card: Scam-Message Triage, English (v0.3)

Labelled English WhatsApp/SMS-style messages for **scam vs. legitimate** classification and **scam-type**
classification, built for triaging instant-payment fraud (Pix, UPI, Zelle, SPEI, Faster Payments, bank transfer,
wallets, gift cards, crypto).

| | |
|---|---|
| Language | English (`en`); payment rails, currencies, banks and couriers are drawn from BR, IN, US, UK, MX and EU |
| Tasks | binary `is_scam`; 11-way `label` (10 scam types + `legit`) |
| Size | 7,598 synthetic + 4,518 real legit (UCI, downloaded on demand) + 230 hand-written challenge messages |
| Files | `synthetic_{train,val,test}.jsonl`, `challenge.jsonl`, `challenge_v2.jsonl`, `challenge_v3.jsonl` |
| Generator | `scam_triage/synth/` (deterministic, seed 13): `python scripts/build_dataset.py` |
| License | Synthetic and hand-written data: CC BY 4.0. UCI SMS Spam Collection: CC BY 4.0, not redistributed here |

## Labels

| `label` | Scam type | What it covers |
|---|---|---|
| `family_impersonation` | Fake relative or friend | "Hi Mum, new number", grandchild-in-trouble, friend on a borrowed phone |
| `fake_payment_receipt` | Fake payment receipt / overpayment | "sent you money by mistake, send it back", forged receipts, marketplace buyer "pending" payments |
| `bank_impersonation` | Fake bank agent | fake fraud alerts, call-this-number, "safe account", remote-access apps, cash/gold courier |
| `delivery_fee` | Fake delivery / parcel fee | held parcel, customs/redelivery fee, address-confirmation links |
| `toll_fine_tax` | Fake fine, toll or tax notice | unpaid tolls, tax refunds, traffic/parking fines, police and "digital arrest" threats |
| `account_phishing` | Account suspension / login phishing | locked/suspended accounts, billing failures, tech-support refund scams |
| `verification_code_theft` | Verification code theft | "a code was sent to you by mistake, forward it" (WhatsApp/bank takeover) |
| `prize_lottery` | Fake prize / giveaway | lotteries, loyalty-point expiry, "pay shipping for your free gift" |
| `job_task` | Fake job / task scam | like/rate-for-cash, recharge-to-withdraw, lucky/combo orders |
| `investment_crypto` | Investment / crypto scam | guaranteed returns, trading mentors, crypto doubling, relationship openers |
| `legit` | Legitimate | personal chat, real bank/wallet/Pix/UPI receipts, OTPs, deliveries, appointments, recruiters |

## Fields

```json
{"id": "en-syn-000123", "text": "...", "label": "delivery_fee", "is_scam": 1,
 "template_id": "delivery_fee/04", "split": "train", "source": "synthetic", "lang": "en"}
```

`template_id` is `null` for real and hand-written messages. `source` is `synthetic`, `uci_sms_ham`, `handwritten`,
`handwritten_v2` or `handwritten_v3`.

## How it was built

**Synthetic (7,598).** 212 hand-written templates (12–14 per scam type, 88 legit) filled with randomized slots:
names, relatives, amounts in one currency per message ($, £, €, R$, ₹, MXN), rails, banks, stores, couriers, phone
numbers, Pix/UPI keys, account details, and links. Scam links are generated phishing-style domains (look-alikes,
risky TLDs, shorteners, raw IPs). Legit links are the official site of the entity the message names. Light noise:
text-speak, typos, casing, emoji.

Legit templates deliberately include **hard negatives**: OTP messages ("do not share this code"), real fraud alerts
that point to the app or the back of the card, Pix/UPI/Zelle/wallet receipts, people asking family or friends for small
amounts, "lost my phone but kept my number", and real recruiter messages.

**Splits are by template**, not by message. Each scam type has 8–9 train / 2 val / 2–3 test templates, and legit has
57 / 13 / 18. Validation and test therefore measure generalization to **unseen phrasings**, not memorized templates.

| Split | Messages | Scam | Legit | Templates |
|---|---|---|---|---|
| train | 4,931 | 2,362 | 2,569 | 138 |
| val | 1,174 | 584 | 590 | 33 |
| test | 1,493 | 665 | 828 | 41 |

**Real legit negatives (4,518).** "Ham" messages from the
[UCI SMS Spam Collection](https://archive.ics.uci.edu/dataset/228/sms+spam+collection) (Almeida & Gómez Hidalgo,
2011), seeded 70/15/15 random split (3,164 / 677 / 677). Fetched into `data/external/` by the build script and not
committed. UCI "spam" is not used: it is mostly marketing and premium-rate spam that doesn't map to payment-scam types.

**Hand-written challenge sets (230).** Written independently of the generator, modelled on publicly reported scams
(UK "Hi Mum", US toll and USPS smishing, Indian KYC / "digital arrest" / task scams, Brazilian Pix refund and fake
central-bank-agent scams, pig-butchering openers) and on tricky legit messages.

| File | Scam / legit | Status |
|---|---|---|
| `challenge.jsonl` (v1) | 50 / 40 | Inspected after v0.1 to find data gaps (not blind) |
| `challenge_v2.jsonl` | 40 / 40 | Committed before v0.2, blind for v0.2, inspected before v0.3 |
| `challenge_v3.jsonl` | 30 / 30 | Committed before v0.3, **blind**. Use this for honest numbers |

Git history timestamps show that each challenge set was committed before the changes it evaluates.

## Intended use

- Training and evaluating lightweight, explainable scam-triage models.
- Benchmarking precision/recall at **low false-positive rates**, where a consumer-facing checker has to operate.
- A starting point for PT-BR/ES versions: the taxonomy and template format are language-independent.

**Not intended** as a measure of real-world prevalence or as the only training data for a production fraud system.

## Known limitations and biases

- **Synthetic distribution.** Scam phrasings come from one author's templates. Held-out-template scores are optimistic
  about truly novel scam scripts. The small challenge sets partly compensate.
- **Dated real negatives.** UCI ham is 2000s UK/Singapore SMS, not modern WhatsApp chat or app notifications.
- **Single messages only.** Conversation-starter scams (pig butchering, "wrong number" openers) often look harmless
  in their first message.
- **Brand and amount priors.** Amounts are uniform within ranges and brands are sampled independently of country, so
  some combinations are unrealistic ("Correios" with US dollars).
- **Label granularity.** Some scams straddle types (a KYC bank phish is both `bank_impersonation` and
  `account_phishing`). Labels follow the template's primary intent.

## Privacy and safety

- Contains no real personal data. Names are common first names. Phone numbers, account numbers and Pix/UPI keys are
  random digits and **may coincide with real ones**. Do not call or pay them.
- Generated scam domains are random and may coincide with real (possibly malicious) domains. Do not visit them.
- The templates describe scam *patterns* that are already widely published by banks, regulators and consumer bodies,
  so the dataset adds negligible uplift to scammers.

## Citation

```
@misc{gaikwad2026scamtriage,
  author = {Amogh Gaikwad},
  title  = {Scam-Message Triage: an explainable, rail-agnostic scam classifier and dataset},
  year   = {2026},
  url    = {https://github.com/ag2502/scam-message-triage}
}
```

UCI SMS Spam Collection: Almeida, T.A., Gómez Hidalgo, J.M., Yamakami, A. *Contributions to the Study of SMS Spam
Filtering: New Collection and Results.* DocEng 2011.
