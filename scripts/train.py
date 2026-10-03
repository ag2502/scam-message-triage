"""Train the triage model and save it to models/<lang>/triage.joblib.

    python scripts/train.py [--lang en] [--synthetic-only]
"""

from __future__ import annotations

import argparse
import json

from scam_triage.dataset import load_split
from scam_triage.model import TriageModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="en")
    ap.add_argument("--synthetic-only", action="store_true", help="exclude real UCI ham negatives")
    args = ap.parse_args()

    train = load_split("train", args.lang, include_real=not args.synthetic_only)
    val = load_split("val", args.lang, include_real=not args.synthetic_only)
    print(f"train={len(train)} val={len(val)}")
    model = TriageModel.train(train, val, lang=args.lang)
    path = model.save()
    print(f"saved {path}")
    print(json.dumps({"thresholds": model.thresholds, **model.meta}, indent=2))


if __name__ == "__main__":
    main()
