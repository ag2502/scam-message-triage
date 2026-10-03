"""Render a scripted page frame by frame and encode it as video (with a synthesized soundtrack).

    python scripts/record_demo.py                       # film.html -> site/assets/video/film.{mp4,webm}
    python scripts/record_demo.py --preview 2,24,45     # save stills to inspect the composition
    python scripts/record_demo.py --page demo.html --name demo --no-audio

The page must expose window.film (or window.demo) = { renderAt(t), DURATION, CHAPTERS, ready,
and optionally CUES + MUSIC }. Every frame comes from the deterministic renderAt(t), so the
result is smooth regardless of machine speed. If CUES are present, scripts/film_audio.py
synthesizes music and sound effects aligned to them.
Needs: uv pip install -e ".[web]" && playwright install chromium
"""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
import film_audio  # noqa: E402

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
    ap.add_argument("--page", default="film.html")
    ap.add_argument("--name", default="film", help="output basename in site/assets/video/")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--scale", type=float, default=1.5, help="device scale factor (1.5 -> 1920x1080)")
    ap.add_argument("--preview", help="comma-separated times (s) to save as stills instead of recording")
    ap.add_argument("--poster-time", type=float, default=31.6)
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    srv = serve()
    OUT.mkdir(parents=True, exist_ok=True)
    frames = Path(tempfile.mkdtemp(prefix="film-frames-"))
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 720}, device_scale_factor=args.scale)
            page.goto(f"http://127.0.0.1:{srv.server_port}/{args.page}?record", wait_until="networkidle")
            page.evaluate("(window.film || window.demo).ready")
            meta = page.evaluate("(() => { const f = window.film || window.demo; return {d: f.DURATION, ch: f.CHAPTERS, cues: f.CUES || null, music: f.MUSIC || null}; })()")
            stage = page.query_selector("[data-stage]")

            def shot(t: float, path: Path, kind: str = "jpeg") -> None:
                page.evaluate("t => (window.film || window.demo).renderAt(t)", t)
                opts = {"path": str(path), "type": kind}
                if kind == "jpeg":
                    opts["quality"] = 92
                stage.screenshot(**opts)

            if args.preview:
                for t in (float(x) for x in args.preview.split(",")):
                    path = frames.parent / f"{args.name}-preview-{t:05.1f}.png"
                    shot(t, path, "png")
                    print(path)
                browser.close()
                return

            n = int(meta["d"] * args.fps)
            for i in range(n):
                shot(i / args.fps, frames / f"{i:05d}.jpg")
                if i % (args.fps * 10) == 0:
                    print(f"frame {i}/{n}", flush=True)
            shot(args.poster_time, OUT / f"{args.name}-poster.jpg")
            browser.close()

        (OUT / f"{args.name}-chapters.json").write_text(json.dumps(meta["ch"], indent=2))
        audio = None
        if meta["cues"] and not args.no_audio:
            audio = frames / "audio.wav"
            film_audio.write_wav(str(audio), film_audio.render(meta["cues"], meta["music"], meta["d"]))
            print("synthesized soundtrack")

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        src = [ffmpeg, "-y", "-loglevel", "error", "-framerate", str(args.fps), "-i", str(frames / "%05d.jpg")]
        if audio:
            src += ["-i", str(audio)]
        vf = ["-vf", "scale=in_range=pc:out_range=tv,format=yuv420p", "-color_range", "tv"]
        encodings = {
            f"{args.name}.mp4": ["-c:v", "libx264", "-preset", "slow", "-crf", "21", "-movflags", "+faststart"]
                                + (["-c:a", "aac", "-b:a", "160k"] if audio else []),
            f"{args.name}.webm": ["-c:v", "libvpx-vp9", "-crf", "33", "-b:v", "0", "-row-mt", "1", "-deadline", "good"]
                                 + (["-c:a", "libopus", "-b:a", "128k"] if audio else []),
        }
        for name, codec in encodings.items():
            subprocess.run([*src, *vf, *codec, "-shortest", str(OUT / name)], check=True)
            print(f"wrote {OUT / name} ({(OUT / name).stat().st_size / 1e6:.1f} MB)")
        print(f"wrote {args.name}-poster.jpg, {args.name}-chapters.json")
    finally:
        shutil.rmtree(frames, ignore_errors=True)
        srv.shutdown()


if __name__ == "__main__":
    main()
