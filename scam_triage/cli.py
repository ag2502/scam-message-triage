"""Command line: `scam-triage "message"` or pipe text on stdin."""

from __future__ import annotations

import argparse
import json
import sys

from scam_triage.reply import format_reply
from scam_triage.triage import triage_text


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="scam-triage", description="Check a message for scam patterns.")
    ap.add_argument("text", nargs="?", help="message text (reads stdin if omitted)")
    ap.add_argument("--lang", default="en")
    ap.add_argument("--json", action="store_true", help="print the full result as JSON")
    args = ap.parse_args(argv)

    text = args.text if args.text is not None else sys.stdin.read()
    if not text.strip():
        ap.error("no message given")
    result = triage_text(text, lang=args.lang)
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) if args.json else format_reply(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
