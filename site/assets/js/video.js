// Demo video player: chapters (from chapters.json written by scripts/record_demo.py) and time display.
import { $, esc } from "./ui.js";

const fmt = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

export async function initVideo() {
  const video = $("[data-video]");
  const list = $("[data-chapters]");
  const time = $("[data-video-time]");
  if (!video) return;

  let chapters = [];
  try { chapters = await (await fetch(new URL("../video/chapters.json", import.meta.url))).json(); } catch { return; }
  list.innerHTML = chapters.map((c, i) => `<li><button type="button" data-ch="${i}"><time>${fmt(c.t)}</time><span>${esc(c.title)}</span></button></li>`).join("");
  const buttons = [...list.querySelectorAll("button")];

  list.addEventListener("click", (e) => {
    const b = e.target.closest("[data-ch]");
    if (!b) return;
    const t = chapters[+b.dataset.ch].t;
    // Setting currentTime before metadata has loaded is ignored, so wait for it if needed.
    if (video.readyState >= 1) video.currentTime = t;
    else video.addEventListener("loadedmetadata", () => (video.currentTime = t), { once: true });
    video.play().catch(() => {});
  });
  const sync = () => {
    time.textContent = `${fmt(video.currentTime)} / ${fmt(video.duration || 0)}`;
    let idx = 0;
    chapters.forEach((c, i) => { if (video.currentTime >= c.t - 0.05) idx = i; });
    buttons.forEach((b, i) => b.classList.toggle("is-active", i === idx));
  };
  video.addEventListener("timeupdate", sync);
  video.addEventListener("loadedmetadata", sync);
}
