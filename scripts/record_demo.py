"""Render site/demo.html frame by frame and encode the demo video.

    python scripts/record_demo.py                 # -> site/assets/video/demo.mp4, poster.jpg, chapters.json
    python scripts/record_demo.py --preview 6,20,28  # save a few stills to inspect the composition

Every frame is produced by calling the page's deterministic renderAt(t), so the video is
smooth regardless of machine speed. Needs: uv pip install -e ".[web]" && playwright install chromium
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "assets" / "video"


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve() -> http.server.ThreadingHTTPServer:
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(SITE)))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--scale", type=float, default=1.5, help="device scale factor (1.5 -> 1920x1080)")
    ap.add_argument("--preview", help="comma-separated times (s) to save as stills instead of recording")
    ap.add_argument("--poster-time", type=float, default=21.0)
    args = ap.parse_args()

    srv = serve()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = Path(tempfile.mkdtemp(prefix="demo-frames-"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=args.scale)
            page.goto(f"http://127.0.0.1:{srv.server_port}/demo.html?record", wait_until="networkidle")
            page.evaluate("window.demo.ready")
            duration = page.evaluate("window.demo.DURATION")
            stage = page.query_selector("[data-stage]")

            def shot(t: float, path: Path, kind: str = "jpeg") -> None:
                page.evaluate("t => window.demo.renderAt(t)", t)
                opts = {"path": str(path), "type": kind}
                if kind == "jpeg":
                    opts["quality"] = 92
                stage.screenshot(**opts)

            if args.preview:
                for t in (float(x) for x in args.preview.split(",")):
                    path = frames.parent / f"demo-preview-{t:05.1f}.png"
                    shot(t, path, "png")
                    print(path)
                browser.close()
                return

            n = int(duration * args.fps)
            for i in range(n):
                shot(i / args.fps, frames / f"{i:05d}.jpg")
                if i % (args.fps * 5) == 0:
                    print(f"frame {i}/{n}")
            shot(args.poster_time, OUT / "poster.jpg")
            chapters = page.evaluate("window.demo.CHAPTERS")
            browser.close()

        (OUT / "chapters.json").write_text(json.dumps(chapters, indent=2))
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        src = [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", str(frames / "%05d.jpg"),
               "-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv"]
        encodings = {
            "demo.mp4": ["-c:v", "libx264", "-preset", "slow", "-crf", "22", "-movflags", "+faststart"],
            "demo.webm": ["-c:v", "libvpx-vp9", "-crf", "34", "-b:v", "0", "-row-mt", "1", "-deadline", "good"],
        }
        for name, codec in encodings.items():
            subprocess.run([*src, *codec, str(OUT / name)], check=True)
            print(f"wrote {OUT / name} ({(OUT / name).stat().st_size / 1e6:.1f} MB)")
        print("wrote poster.jpg, chapters.json")
    finally:
        shutil.rmtree(frames, ignore_errors=True)
        srv.shutdown()


if __name__ == "__main__":
    main()
