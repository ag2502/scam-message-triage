// Tiny window manager for the toolbox: drag, resize, focus, minimize, maximize, close, dock.
// Below 900px it becomes a tabbed app switcher (one window at a time, no dragging).
import { $, $$, esc, reducedMotion, whenNear } from "./ui.js";

const MOBILE = "(max-width: 900px)";
const FIRST_OPEN = ["xray", "checker", "terminal"]; // opened (in this order) the first time the desktop is seen

export function initOS({ state }) {
  const os = $("[data-os]");
  if (!os) return;
  const desk = $("[data-os-desk]", os);
  const dock = $("[data-os-dock]", os);
  const activeName = $("[data-os-active]", os);
  const wins = new Map($$(".oswin", desk).map((w) => [w.dataset.win, w]));
  const mq = window.matchMedia(MOBILE);
  let z = 10;

  setInterval(() => ($("[data-os-clock]", os).textContent = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })), 15000);

  // ---------- dock ----------
  dock.innerHTML = [...wins.values()].map((w) => `
    <button type="button" class="dock__app" data-dock="${w.dataset.win}" aria-label="${esc(w.dataset.title)}" title="${esc(w.dataset.title)}">
      <span class="dock__tile"><i class="ph-fill ${w.dataset.icon}"></i></span><span class="dock__label">${esc(w.dataset.title)}</span>
    </button>`).join("");
  const dockBtn = (id) => $(`[data-dock="${id}"]`, dock);

  // Magnification: scale icons by distance to the pointer (transform only).
  const apps = $$(".dock__app", dock);
  let raf = 0;
  dock.addEventListener("pointermove", (e) => {
    if (mq.matches || reducedMotion()) return;
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => apps.forEach((a) => {
      const r = a.getBoundingClientRect();
      const d = Math.abs(e.clientX - (r.left + r.width / 2));
      a.style.setProperty("--mag", (1 + Math.max(0, 1 - d / 160) * 0.55).toFixed(3));
    }));
  });
  dock.addEventListener("pointerleave", () => apps.forEach((a) => a.style.setProperty("--mag", 1)));

  // ---------- geometry ----------
  const deskBox = () => ({ w: desk.clientWidth, h: desk.clientHeight });
  function place(w) {
    const [x, y, ww, hh] = w.dataset.geo.split(",").map(Number);
    const { w: dw, h: dh } = deskBox();
    const width = Math.min(ww, dw - 24), height = Math.min(hh, dh - 24);
    w.style.width = `${width}px`;
    w.style.height = `${height}px`;
    w.style.left = `${Math.max(12, Math.min(x, dw - width - 12))}px`;
    w.style.top = `${Math.max(12, Math.min(y, dh - height - 12))}px`;
  }

  // ---------- state ----------
  function focus(w) {
    wins.forEach((o) => o.classList.toggle("is-active", o === w));
    w.style.zIndex = ++z;
    activeName.textContent = w.dataset.title;
    apps.forEach((a) => a.classList.toggle("is-front", a.dataset.dock === w.dataset.win));
    if (mq.matches) wins.forEach((o) => (o.hidden = o !== w));
  }
  function open(id, { animate = true } = {}) {
    const w = wins.get(id);
    if (!w) return;
    const wasHidden = w.hidden || w.classList.contains("is-min");
    if (!w.dataset.placed) { place(w); w.dataset.placed = "1"; }
    w.hidden = false;
    w.classList.remove("is-min");
    dockBtn(id)?.classList.add("is-open");
    focus(w);
    if (wasHidden && animate && !reducedMotion() && !mq.matches) {
      const d = dockBtn(id).getBoundingClientRect(), r = w.getBoundingClientRect();
      const dx = d.left + d.width / 2 - (r.left + r.width / 2), dy = d.top - (r.top + r.height / 2);
      w.animate([{ transform: `translate(${dx}px, ${dy}px) scale(0.12)`, opacity: 0 }, { transform: "none", opacity: 1 }],
        { duration: 420, easing: "cubic-bezier(0.16, 1, 0.3, 1)" });
    }
    w.dispatchEvent(new CustomEvent("os:open"));
  }
  function minimize(w) {
    if (mq.matches) return;
    const d = dockBtn(w.dataset.win).getBoundingClientRect(), r = w.getBoundingClientRect();
    const done = () => { w.classList.add("is-min"); w.hidden = true; };
    if (reducedMotion()) return done();
    w.animate([{ transform: "none", opacity: 1 }, { transform: `translate(${d.left + d.width / 2 - (r.left + r.width / 2)}px, ${d.top - (r.top + r.height / 2)}px) scale(0.1)`, opacity: 0 }],
      { duration: 360, easing: "cubic-bezier(0.7, 0, 0.84, 0)" }).onfinish = done;
  }
  function close(w) {
    if (mq.matches) return;
    const done = () => { w.hidden = true; w.classList.remove("is-max"); dockBtn(w.dataset.win)?.classList.remove("is-open", "is-front"); };
    if (reducedMotion()) return done();
    w.animate([{ transform: "none", opacity: 1 }, { transform: "scale(0.94)", opacity: 0 }], { duration: 180 }).onfinish = done;
  }
  const toggleMax = (w) => { if (!mq.matches) { w.classList.toggle("is-max"); focus(w); } };

  // ---------- events ----------
  dock.addEventListener("click", (e) => {
    const b = e.target.closest("[data-dock]");
    if (!b) return;
    const w = wins.get(b.dataset.dock);
    if (!w.hidden && w.classList.contains("is-active") && !mq.matches) minimize(w);
    else open(b.dataset.dock);
  });
  desk.addEventListener("dblclick", (e) => {
    const icon = e.target.closest(".os__icon");
    if (icon) open(icon.dataset.open);
    const bar = e.target.closest(".oswin__bar");
    if (bar && !e.target.closest("button")) toggleMax(bar.parentElement);
  });
  desk.addEventListener("click", (e) => {
    const icon = e.target.closest(".os__icon");
    if (icon && (e.detail === 0 || mq.matches)) open(icon.dataset.open); // keyboard / touch: single activation
  });
  wins.forEach((w) => {
    w.addEventListener("pointerdown", () => focus(w), true);
    $("[data-win-close]", w).addEventListener("click", () => close(w));
    $("[data-win-min]", w).addEventListener("click", () => minimize(w));
    $("[data-win-max]", w).addEventListener("click", () => toggleMax(w));
    dragger(w, $(".oswin__bar", w), "move");
    dragger(w, $("[data-win-grip]", w), "resize");
  });

  function dragger(w, handle, mode) {
    let sx, sy, ox, oy, ow, oh, active = false;
    handle.addEventListener("pointerdown", (e) => {
      if (mq.matches || e.button !== 0 || e.target.closest("button") || w.classList.contains("is-max")) return;
      active = true; sx = e.clientX; sy = e.clientY;
      ox = w.offsetLeft; oy = w.offsetTop; ow = w.offsetWidth; oh = w.offsetHeight;
      handle.setPointerCapture(e.pointerId);
      w.classList.add(mode === "move" ? "is-moving" : "is-resizing");
      e.preventDefault();
    });
    handle.addEventListener("pointermove", (e) => {
      if (!active) return;
      const { w: dw, h: dh } = deskBox();
      const dx = e.clientX - sx, dy = e.clientY - sy;
      if (mode === "move") {
        w.style.left = `${Math.min(Math.max(ox + dx, -ow + 120), dw - 120)}px`;
        w.style.top = `${Math.min(Math.max(oy + dy, 0), dh - 44)}px`;
      } else {
        w.style.width = `${Math.min(Math.max(ow + dx, 300), dw - ox)}px`;
        w.style.height = `${Math.min(Math.max(oh + dy, 220), dh - oy)}px`;
      }
    });
    const end = () => { active = false; w.classList.remove("is-moving", "is-resizing"); };
    handle.addEventListener("pointerup", end);
    handle.addEventListener("pointercancel", end);
  }

  // Anything on the page can open a window: <button data-open="api">
  document.addEventListener("click", (e) => {
    const t = e.target.closest("[data-open]");
    if (!t || t.closest("[data-os-desk]")) return;
    document.getElementById("toolbox").scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth" });
    setTimeout(() => open(t.dataset.open), reducedMotion() ? 0 : 450);
  });
  state.openWindow = open;

  // Responsive mode switch
  const applyMode = () => {
    os.classList.toggle("is-mobile", mq.matches);
    if (mq.matches) {
      const front = [...wins.values()].find((w) => w.classList.contains("is-active")) || wins.get("checker");
      wins.forEach((w) => { w.classList.remove("is-max", "is-min"); dockBtn(w.dataset.win).classList.add("is-open"); });
      focus(front);
    } else {
      wins.forEach((w) => { if (w.dataset.placed) place(w); });
    }
  };
  mq.addEventListener("change", applyMode);

  // First view: open a few windows in a cascade.
  wins.forEach((w) => (w.hidden = true));
  applyMode();
  whenNear(os, () => {
    if (mq.matches) { open("checker", { animate: false }); return; }
    FIRST_OPEN.forEach((id, i) => setTimeout(() => open(id), reducedMotion() ? 0 : 160 * i));
  }, "-120px");
}
