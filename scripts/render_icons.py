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
# Android: adaptive-icon foreground (glyph inside the 66/108 safe zone, transparent) + legacy icon per density.
RES = ROOT / "mobile" / "android" / "app" / "src" / "main" / "res"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
ANDROID = [(RES / f"mipmap-{d}" / "ic_launcher_foreground.png", int(108 * k), 0.0, 0.40, "transparent") for d, k in DENSITIES.items()] + \
          [(RES / f"mipmap-{d}" / "ic_launcher.png", int(48 * k), 0.22, 0.6, None) for d, k in DENSITIES.items()]
# iOS app icon (single 1024 image, no transparency, no rounding: iOS applies the mask).
IOS = [(ROOT / "mobile" / "ios" / "App" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png", 1024, 0.0, 0.56, None)]


def main() -> None:
    vendor = ROOT / "site" / "assets" / "vendor" / "phosphor"
    tmp = vendor / "_icon.html"  # next to fill.css so the icon font loads over file://
    with sync_playwright() as p:
        b = p.chromium.launch()
        jobs = [(OUT / n, s_, r, g, None) for n, s_, r, g in ICONS] + ANDROID + IOS
        for path, size, radius, glyph, bg in jobs:
            path.parent.mkdir(parents=True, exist_ok=True)
            pg = b.new_page(viewport={"width": size, "height": size})
            tmp.write_text(PAGE.format(s=size, r=int(size * radius), f=int(size * glyph),
                                       bg=bg or "linear-gradient(160deg,#3a5cf0,#2240c4)"))
            pg.goto(tmp.as_uri())
            pg.evaluate("document.fonts.ready")
            pg.wait_for_timeout(150)
            pg.locator(".i").screenshot(path=str(path), omit_background=bg == "transparent")
            pg.close()
            print("wrote", path.relative_to(ROOT))
        b.close()
    tmp.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
