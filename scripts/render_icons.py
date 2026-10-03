"""Render the app icons (PNG) from the brand mark: site/assets/img/icon-*.png

    python scripts/render_icons.py
"""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "assets" / "img"
PAGE = """<!doctype html><html><head><link rel="stylesheet" href="fill.css">
<style>html,body{{margin:0;background:transparent}}
.i{{width:{s}px;height:{s}px;display:grid;place-items:center;background:{bg};border-radius:{r}px}}
.i i{{font-size:{f}px;color:#fff}}</style></head>
<body><div class="i"><i class="ph-fill ph-shield-check"></i></div></body></html>"""

# name, size, corner radius (fraction), glyph size (fraction): maskable keeps the glyph in the safe zone.
ICONS = [("icon-192.png", 192, 0.22, 0.6), ("icon-512.png", 512, 0.22, 0.6),
         ("icon-maskable-512.png", 512, 0.0, 0.46), ("apple-touch-icon.png", 180, 0.0, 0.6)]


def main() -> None:
    vendor = ROOT / "site" / "assets" / "vendor" / "phosphor"
    tmp = vendor / "_icon.html"  # next to fill.css so the icon font loads over file://
    with sync_playwright() as p:
        b = p.chromium.launch()
        for name, size, radius, glyph in ICONS:
            pg = b.new_page(viewport={"width": size, "height": size})
            tmp.write_text(PAGE.format(s=size, r=int(size * radius), f=int(size * glyph),
                                       bg="linear-gradient(160deg,#3a5cf0,#2240c4)"))
            pg.goto(tmp.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(200)
            pg.locator(".i").screenshot(path=str(OUT / name), omit_background=True)
            print("wrote", name)
        b.close()
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
