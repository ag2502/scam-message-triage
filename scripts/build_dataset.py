"""Generate the synthetic corpus and fetch real negatives.

    python scripts/build_dataset.py [--lang en] [--seed 13] [--no-download]
"""

from __future__ import annotations

import argparse
from collections import Counter

from scam_triage.dataset import download_uci, load_uci_ham, synthetic_path, write_jsonl
from scam_triage.synth import generate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--no-download", action="store_true", help="skip fetching the UCI ham corpus")
    args = ap.parse_args()

    rows = generate(args.lang, seed=args.seed)
    for split in ("train", "val", "test"):
        part = [r for r in rows if r["split"] == split]
        write_jsonl(part, synthetic_path(args.lang, split))
        counts = Counter(r["label"] for r in part)
        print(f"synthetic {split:5s} n={len(part):5d} " + " ".join(f"{k}={v}" for k, v in sorted(counts.items())))

    if args.lang == "en" and not args.no_download:
        download_uci()
        ham = load_uci_ham(seed=args.seed)
        print("uci ham   " + " ".join(f"{s}={sum(r['split'] == s for r in ham)}" for s in ("train", "val", "test")))


if __name__ == "__main__":
    main()
