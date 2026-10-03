"""Static checks for the website: offline precache list, manifest, icons."""

import json
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"


def precache() -> list[str]:
    src = (SITE / "sw.js").read_text()
    return re.findall(r'"(/[^"]*)"', src.split("const PRECACHE")[1].split("];")[0])


def test_every_site_script_is_precached_and_exists():
    listed = set(precache())
    scripts = {f"/assets/js/{p.name}" for p in (SITE / "assets/js").glob("*.js") if p.name != "film.js"}
    assert scripts <= listed, f"missing from sw.js PRECACHE: {sorted(scripts - listed)}"
    for path in listed:
        target = SITE / ("index.html" if path == "/" else path.lstrip("/"))
        assert target.exists(), path


def test_manifest_share_target_and_icons():
    m = json.loads((SITE / "manifest.webmanifest").read_text())
    assert m["share_target"]["method"] == "GET" and "text" in m["share_target"]["params"].values()
    assert any(i.get("purpose") == "maskable" for i in m["icons"])
    for icon in m["icons"]:
        assert (SITE / icon["src"].lstrip("/")).exists(), icon["src"]
