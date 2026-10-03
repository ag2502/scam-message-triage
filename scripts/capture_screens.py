"""Capture real screenshots of the site for the film's "everywhere" scene.

    python scripts/capture_screens.py   # -> site/assets/video/shot-{chat,toolbox,bank}.jpg
"""

from __future__ import annotations

import functools
import http.server
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "assets" / "video"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> None:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/"
    hide = ".nav{display:none!important} .js .reveal{opacity:1!important;transform:none!important}"
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2, color_scheme="light")
            pg.goto(url, wait_until="networkidle")
            pg.add_style_tag(content=hide)
            pg.wait_for_timeout(1500)
            # Hero chat: one forwarded scam, the verdict and "Why?"
            pg.click("[data-chip='0']")
            pg.wait_for_selector(".wa-verdict", timeout=20000)
            pg.wait_for_timeout(600)
            pg.click("[data-act='why']")
            pg.wait_for_timeout(1800)
            pg.query_selector("#chat").screenshot(path=str(OUT / "shot-chat.jpg"), type="jpeg", quality=88)
            # Toolbox desktop with a checker result
            pg.evaluate("document.querySelector('[data-os]').scrollIntoView({block: 'center'})")
            pg.wait_for_timeout(1800)
            pg.click("[data-dock='checker']")
            pg.wait_for_timeout(400)
            pg.click("[data-sample='3']")
            pg.wait_for_timeout(1200)
            pg.query_selector("[data-os]").screenshot(path=str(OUT / "shot-toolbox.jpg"), type="jpeg", quality=86)
            # Bank flow sheet
            pg.click("[data-dock='bank']")
            pg.wait_for_timeout(1200)
            pg.query_selector("[data-win='bank']").screenshot(path=str(OUT / "shot-bank.jpg"), type="jpeg", quality=88)
            b.close()
    finally:
        srv.shutdown()
    print("wrote shot-chat.jpg, shot-toolbox.jpg, shot-bank.jpg")


if __name__ == "__main__":
    main()
