"""The in-browser engine (site/assets/js/engine.js) must reproduce Python's triage().

Runs the JS engine in headless Chromium via Playwright. Skipped when Playwright or the
exported model is missing (install with: uv pip install -e ".[web]" && playwright install chromium).
"""

import functools
import http.server
import threading
from pathlib import Path

import pytest

from scam_triage.dataset import DATA_DIR, load_split, read_jsonl
from scam_triage.triage import triage

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
pw = pytest.importorskip("playwright.sync_api")
pytestmark = pytest.mark.skipif(not (SITE / "assets/model/en.json").exists(), reason="run scripts/export_web.py first")

EDGE_CASES = [
    "Hi mãe 😩😩 it's João, novo número. Can you send R$1.200 by Pix? urgent!!",
    "Itaú: Pix received R$85,00 from Marina Costa.",
    "Your Uber code is 4821. Never share this code.",
    "Do not share this code with anyone. We will never ask you to move your money to a safe account.",
    "visit https://user@usps.com-track.top:8080/x?y=1 now",
    "Paytm: ₹1,200 paid to Reliance Fresh. UPI Ref 4209118823.",
    "Call +44 7700 900123 or 0800 555 0193 today",
    "ＵＲＧＥＮＴ​ pay ｎｏｗ at bit.ly/abc",
    "ok",
    "   ",
]


@pytest.fixture(scope="module")
def page():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    with pw.sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page()
        pg.goto(f"http://127.0.0.1:{server.server_port}/assets/model/en.json")
        pg.evaluate(
            """async () => {
                const { Engine } = await import('/assets/js/engine.js');
                window.__engine = await Engine.load('/assets/model/en.json');
            }"""
        )
        yield pg
        browser.close()
    server.shutdown()


def _texts() -> list[str]:
    texts = list(EDGE_CASES)
    for path in sorted(DATA_DIR.joinpath("en").glob("challenge*.jsonl")):
        texts += [r["text"] for r in read_jsonl(path)]
    texts += [r["text"] for r in load_split("test")[::7]]
    return [t for t in texts if t.strip()]


def test_js_engine_matches_python(page):
    texts = _texts()
    js = page.evaluate("ts => ts.map(t => window.__engine.triage(t))", texts)
    mismatches = []
    for text, j in zip(texts, js):
        py = triage(text).to_dict()
        same = (
            abs(py["risk_score"] - j["risk_score"]) <= 2e-4
            and py["risk_level"] == j["risk_level"]
            and py["scam_type"] == j["scam_type"]
            and py["reasons"] == j["reasons"]
            and py["key_phrases"] == j["key_phrases"]
        )
        if not same:
            mismatches.append((text, {k: py[k] for k in ("risk_score", "risk_level", "scam_type", "key_phrases")},
                               {k: j[k] for k in ("risk_score", "risk_level", "scam_type", "key_phrases")}))
    assert not mismatches, f"{len(mismatches)}/{len(texts)} differ, e.g. {mismatches[:3]}"


def test_signals_match_python(page):
    from scam_triage.signals import detect

    texts = _texts()
    js = page.evaluate("ts => ts.map(t => window.__engine.detect(t).map(h => [h.id, h.evidence]))", texts)
    for text, j in zip(texts, js):
        assert [[h.id, h.evidence] for h in detect(text)] == j, text
