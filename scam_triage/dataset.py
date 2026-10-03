"""Dataset assembly: synthetic corpus + optional real-world negatives.

Real legitimate SMS come from the UCI SMS Spam Collection (CC BY 4.0, Almeida &
Hidalgo 2011). Only its "ham" messages are used, as extra negatives. The UCI
"spam" class is mostly marketing/premium-rate spam, not payment scams, so it
isn't mapped onto our scam types. The corpus is downloaded on demand into
data/external/ and is not redistributed in this repo.
"""

from __future__ import annotations

import io
import json
import random
import zipfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
EXTERNAL_DIR = DATA_DIR / "external"
UCI_URL = "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip"
UCI_FILE = EXTERNAL_DIR / "SMSSpamCollection"


def write_jsonl(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def download_uci() -> Path:
    if UCI_FILE.exists():
        return UCI_FILE
    EXTERNAL_DIR.mkdir(parents=True, exist_ok=True)
    resp = httpx.get(UCI_URL, follow_redirects=True, timeout=60)
    resp.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        UCI_FILE.write_bytes(z.read("SMSSpamCollection"))
    return UCI_FILE


def load_uci_ham(seed: int = 13, val_frac: float = 0.15, test_frac: float = 0.15) -> list[dict]:
    """UCI ham messages as legit rows with a seeded random split. Empty list if not downloaded."""
    if not UCI_FILE.exists():
        return []
    texts = []
    for line in UCI_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        label, _, text = line.partition("\t")
        if label == "ham" and text.strip():
            texts.append(text.strip())
    texts = sorted(set(texts))
    random.Random(seed).shuffle(texts)
    n_test, n_val = int(len(texts) * test_frac), int(len(texts) * val_frac)
    rows = []
    for i, text in enumerate(texts):
        split = "test" if i < n_test else "val" if i < n_test + n_val else "train"
        rows.append({
            "id": f"en-uci-{i:05d}", "text": text, "label": "legit", "is_scam": 0,
            "template_id": None, "split": split, "source": "uci_sms_ham", "lang": "en",
        })
    return rows


def synthetic_path(lang: str, split: str) -> Path:
    return DATA_DIR / lang / f"synthetic_{split}.jsonl"


def load_split(split: str, lang: str = "en", include_real: bool = True) -> list[dict]:
    rows = read_jsonl(synthetic_path(lang, split))
    if include_real and lang == "en":
        rows += [r for r in load_uci_ham() if r["split"] == split]
    return rows
