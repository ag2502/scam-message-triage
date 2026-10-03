// Site bootstrap: theme, nav, reveal-on-scroll, and the shared model loader.
import { Engine } from "./engine.js";
import { $, $$ } from "./ui.js";
import { initHero } from "./hero.js";
import { initChecker } from "./checker.js";
import { initChannels } from "./channels.js";
import { initXray } from "./xray.js";
import { initGuide } from "./guide.js";
import { initResults } from "./results.js";
import { initVideo } from "./video.js";

document.documentElement.classList.add("js");

// ---------- shared state ----------
const listeners = new Set();
export const state = {
  engine: null,
  lastText: null,
  lastResult: null,
  onResult(fn) { listeners.add(fn); },
  publish(text, result) {
    this.lastText = text;
    this.lastResult = result;
    listeners.forEach((fn) => fn(text, result));
  },
};

let enginePromise = null;
export function loadEngine() {
  if (!enginePromise) {
    enginePromise = Engine.load(new URL("../model/en.json", import.meta.url)).then((e) => (state.engine = e));
    enginePromise.catch(() => { enginePromise = null; });
  }
  return enginePromise;
}

// ---------- theme ----------
function initTheme() {
  const btn = $("[data-theme-toggle]");
  const icon = $("[data-theme-icon]");
  const media = window.matchMedia("(prefers-color-scheme: dark)");
  const current = () => document.documentElement.dataset.theme || (media.matches ? "dark" : "light");
  const paint = () => {
    const dark = current() === "dark";
    icon.className = `ph ${dark ? "ph-sun" : "ph-moon"}`;
    btn.setAttribute("aria-label", dark ? "Switch to light mode" : "Switch to dark mode");
  };
  btn.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    try { localStorage.setItem("theme", next); } catch {}
    paint();
  });
  media.addEventListener("change", paint);
  paint();
}

// ---------- nav ----------
function initNav() {
  const nav = $("[data-nav]");
  const sentinel = document.createElement("div");
  sentinel.style.cssText = "position:absolute;top:0;height:8px;width:1px;";
  document.body.prepend(sentinel);
  new IntersectionObserver(([e]) => nav.classList.toggle("is-scrolled", !e.isIntersecting)).observe(sentinel);

  const toggle = $("[data-menu-toggle]");
  const setOpen = (open) => {
    nav.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.querySelector("i").className = `ph ${open ? "ph-x" : "ph-list"}`;
  };
  toggle.addEventListener("click", () => setOpen(!nav.classList.contains("is-open")));
  $$(".nav__links a").forEach((a) => a.addEventListener("click", () => setOpen(false)));
  document.addEventListener("keydown", (e) => e.key === "Escape" && setOpen(false));

  // Highlight the section in view.
  const links = new Map($$(".nav__links a").map((a) => [a.getAttribute("href").slice(1), a]));
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (!e.isIntersecting) return;
      links.forEach((a) => a.classList.remove("is-active"));
      links.get(e.target.id)?.classList.add("is-active");
    });
  }, { rootMargin: "-45% 0px -50% 0px" });
  links.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
}

// ---------- reveal ----------
function initReveal() {
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("is-in"); io.unobserve(e.target); } });
  }, { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
  $$(".reveal").forEach((el) => io.observe(el));
}

initTheme();
initNav();
initReveal();

const modules = [initHero, initChecker, initChannels, initXray, initGuide, initResults, initVideo];
modules.forEach((init) => {
  try { init({ state, loadEngine }); } catch (err) { console.error(err); }
});

// Start downloading the model once the page is idle, so the hero renders first.
(window.requestIdleCallback || ((fn) => setTimeout(fn, 600)))(() => loadEngine().catch(() => {}));
