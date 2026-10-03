// Scroll cinema: a pinned, scroll-scrubbed walkthrough of one real triage.
// The message, signals, weights, score and verdict all come from the on-device engine.
import { $, $$, esc, reducedMotion, LEVEL_ICON, LEVEL_LABEL } from "./ui.js";
import { signalName } from "./checker.js";

const STORIES = [
  { label: "Hi Mum", text: "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now" },
  { label: "Fake bank", text: "Chase Fraud Alert: we blocked a payment of $1,940. To protect your savings, move your money to the safe account our agent gives you. Call +1 (415) 555 0182 now" },
  { label: "Toll notice", text: "E-ZPass: you have an unpaid toll of $6.89. Pay now to avoid a $50 late fee: ezpass-tollpay.vip" },
];
const MAX_SLOTS = () => (window.innerWidth < 900 ? 4 : 5);
const ARC = Math.PI * 70;

/** Pick the strongest positive signals whose evidence can be located without overlapping. */
export function pickSignals(engine, text, r) {
  const base = engine.nWord + engine.nChar;
  const lower = text.toLowerCase();
  const used = [];
  const picks = [];
  const hits = r.extras.signals
    .map((h) => ({ ...h, w: engine.m.risk.coef[base + engine.signalIds.indexOf(h.id)] }))
    .filter((h) => h.w > 0 && !(h.id === "has_link" && r.extras.signals.some((x) => x.id === "suspicious_link")))
    .sort((a, b) => b.w - a.w);
  for (const h of hits) {
    if (picks.length >= MAX_SLOTS()) break;
    const s = lower.indexOf(h.evidence.toLowerCase());
    const e = s + h.evidence.length;
    const overlaps = s < 0 || used.some(([a, b]) => s < b && e > a);
    if (!overlaps) used.push([s, e]);
    picks.push({ ...h, range: overlaps ? null : [s, e] });
  }
  return picks;
}

export function messageHtml(text, picks) {
  const ranges = picks.map((p, i) => p.range && [...p.range, i]).filter(Boolean).sort((a, b) => a[0] - b[0]);
  const words = (chunk) => chunk.split(/(\s+)/).map((t) => (/^\s+$/.test(t) || !t ? t : `<span class="w">${esc(t)}</span>`)).join("");
  let out = "", pos = 0;
  for (const [s, e, i] of ranges) {
    out += words(text.slice(pos, s));
    out += `<span class="ev" data-ev="${i}"><span class="ev__tag">${esc(signalName(picks[i].id))}</span>${words(text.slice(s, e))}</span>`;
    pos = e;
  }
  return out + words(text.slice(pos));
}

export function initStory({ loadEngine }) {
  const root = $("[data-story]");
  if (!root) return;
  const stage = $("[data-story-stage]", root);
  const msgEl = $("[data-story-msg]", root);
  const slotsEl = $("[data-story-slots]", root);
  const gaugeEl = $("[data-story-gauge]", root);
  const verdictEl = $("[data-story-verdict]", root);
  const caps = $$("[data-cap]", root);
  const progress = $("[data-story-progress]", root);
  const tabs = $("[data-story-tabs]", root);
  let engine = null, current = 0, tl = null, lastWidth = window.innerWidth;

  tabs.innerHTML = STORIES.map((s, i) => `<button type="button" class="chip" role="tab" aria-selected="${i === 0}" aria-pressed="${i === 0}" data-story-tab="${i}">${esc(s.label)}</button>`).join("");
  tabs.addEventListener("click", (e) => {
    const b = e.target.closest("[data-story-tab]");
    if (!b || !engine) return;
    current = +b.dataset.storyTab;
    $$("[data-story-tab]", tabs).forEach((t) => { const on = t === b; t.setAttribute("aria-selected", on); t.setAttribute("aria-pressed", on); });
    build();
  });

  function render(r, picks) {
    const lvl = r.risk_level;
    root.className = `story lvl-${lvl}`;
    msgEl.innerHTML = messageHtml(STORIES[current].text, picks);
    slotsEl.innerHTML = picks.map((p, i) => `
      <li class="slot" data-slot="${i}">
        <span class="slot__empty">signal ${i + 1}</span>
        <span class="slot__full"><i class="ph-fill ph-flag"></i><span class="slot__name">${esc(signalName(p.id))}</span><span class="slot__num" data-w="${p.w.toFixed(2)}">+${p.w.toFixed(2)}</span></span>
      </li>`).join("");
    gaugeEl.innerHTML = `<svg viewBox="0 0 160 96" aria-hidden="true">
        <path class="gauge__track" d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke-width="12" stroke-linecap="round"/>
        <path class="gauge__value" data-arc d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke="var(--lvl)" stroke-width="12" stroke-linecap="round" stroke-dasharray="${ARC}" stroke-dashoffset="${ARC * (1 - r.risk_score)}"/>
        <text class="gauge__num" x="80" y="74" text-anchor="middle" data-num>${Math.round(r.risk_score * 100)}%</text>
        <text class="gauge__cap" x="80" y="92" text-anchor="middle">RISK SCORE</text></svg>`;
    verdictEl.innerHTML = `<span class="badge"><i class="${LEVEL_ICON[lvl]}"></i>${LEVEL_LABEL[lvl]}</span>
      <h3>${esc(r.scam_type_label)}</h3>
      <p>${esc(r.next_steps[0])}</p>
      <small>Computed in ${r.extras.ms.toFixed(1)} ms on this device.</small>`;
    $("[data-story-sr]", root).textContent = `Example: "${STORIES[current].text}". Signals: ${picks.map((p) => signalName(p.id)).join(", ")}. Risk ${Math.round(r.risk_score * 100)} percent: ${r.scam_type_label}.`;
  }

  function build() {
    const gsap = window.gsap;
    if (tl) { tl.scrollTrigger?.kill(); tl.kill(); tl = null; }
    $$(".fly", stage).forEach((n) => n.remove());
    const text = STORIES[current].text;
    engine.triage(text); // warm-up run, so the reported time reflects a normal check
    const r = engine.triage(text);
    const picks = pickSignals(engine, text, r);
    render(r, picks);

    const animate = gsap && window.ScrollTrigger && !reducedMotion();
    root.classList.toggle("is-static", !animate);
    if (!animate) return;

    // Measure source (evidence) and target (slot) boxes in stage coordinates before any tween runs.
    const st = stage.getBoundingClientRect();
    const box = (el) => { const b = el.getBoundingClientRect(); return { x: b.left - st.left, y: b.top - st.top, w: b.width, h: b.height }; };
    const slots = $$(".slot", slotsEl);
    const flies = picks.map((p, i) => {
      const ev = $(`[data-ev="${i}"]`, msgEl);
      if (!ev) return null;
      const from = box(ev), to = box(slots[i]);
      const fly = document.createElement("span");
      fly.className = "fly";
      fly.textContent = ev.textContent.replace(signalName(p.id), "").trim();
      fly.style.cssText = `left:${from.x}px;top:${from.y}px;width:${from.w}px;height:${from.h}px;font-size:${getComputedStyle(msgEl).fontSize}`;
      stage.append(fly);
      // Uniform scale so the phrase keeps its shape; land just after the slot's flag icon.
      const k = Math.min((to.h * 0.62) / from.h, (to.w - 70) / from.w, 1);
      return { fly, dx: to.x + 42 - from.x, dy: to.y + (to.h - from.h * k) / 2 - from.y, sx: k, sy: k };
    });

    const words = $$(".w", msgEl);
    const plain = words.filter((w) => !w.closest(".ev"));
    const evs = $$(".ev", msgEl);
    const arc = $("[data-arc]", gaugeEl), num = $("[data-num]", gaugeEl);
    const counter = { v: 0 };

    tl = gsap.timeline({
      defaults: { ease: "power2.out" },
      scrollTrigger: {
        trigger: root, start: "top top", end: () => `+=${Math.round(window.innerHeight * 3.4)}`,
        scrub: 0.7, pin: true, anticipatePin: 1, invalidateOnRefresh: true,
      },
    });
    const cap = (i, at) => {
      tl.fromTo(caps[i], { autoAlpha: 0, y: 14 }, { autoAlpha: 1, y: 0, duration: 0.25 }, at);
      if (i > 0) tl.to(caps[i - 1], { autoAlpha: 0, y: -14, duration: 0.2 }, at);
    };
    tl.set(caps, { autoAlpha: 0 }, 0);
    tl.fromTo(progress, { scaleX: 0 }, { scaleX: 1, ease: "none", duration: 5.2 }, 0);
    // 1. Message types in
    cap(0, 0);
    tl.from(words, { autoAlpha: 0, y: 16, duration: 0.12, stagger: 0.85 / words.length }, 0.05);
    tl.set(".slot__full", { autoAlpha: 0 }, 0);
    tl.set(arc, { strokeDashoffset: ARC }, 0);
    tl.set(num, { textContent: "0%" }, 0);
    tl.set(verdictEl.children, { autoAlpha: 0, y: 18 }, 0);
    // 2. Evidence lights up
    cap(1, 1.05);
    tl.to(evs, { backgroundSize: "100% 100%", duration: 0.3, stagger: 0.16 }, 1.15);
    tl.fromTo($$(".ev__tag", msgEl), { autoAlpha: 0, y: 8, scale: 0.8 }, { autoAlpha: 1, y: 0, scale: 1, duration: 0.22, stagger: 0.16 }, 1.25);
    // 3. Evidence flies into the signal slots
    cap(2, 2.1);
    tl.to(plain, { opacity: 0.32, duration: 0.3 }, 2.1);
    flies.forEach((f, i) => {
      const at = 2.2 + i * 0.16;
      const slotFull = $(`[data-slot="${i}"] .slot__full`, slotsEl);
      if (f) {
        tl.fromTo(f.fly, { autoAlpha: 0, x: 0, y: 0, scaleX: 1, scaleY: 1 }, { autoAlpha: 1, duration: 0.05 }, at);
        tl.to(f.fly, { x: f.dx, y: f.dy, scaleX: f.sx, scaleY: f.sy, duration: 0.5, ease: "power3.inOut" }, at + 0.02);
        tl.to(f.fly, { autoAlpha: 0, duration: 0.12 }, at + 0.5);
      }
      tl.to(slotFull, { autoAlpha: 1, duration: 0.15 }, at + (f ? 0.48 : 0.1));
    });
    // 4. Weights feed the gauge
    cap(3, 3.3);
    tl.to(arc, { strokeDashoffset: ARC * (1 - r.risk_score), duration: 0.8, ease: "power1.inOut" }, 3.4);
    tl.to(counter, { v: r.risk_score * 100, duration: 0.8, ease: "power1.inOut", onUpdate: () => (num.textContent = `${Math.round(counter.v)}%`) }, 3.4);
    tl.fromTo($$(".slot", slotsEl), { scale: 1 }, { scale: 1.04, duration: 0.12, yoyo: true, repeat: 1, stagger: 0.06 }, 3.35);
    // 5. Verdict
    cap(4, 4.3);
    tl.to(verdictEl.children, { autoAlpha: 1, y: 0, duration: 0.3, stagger: 0.08 }, 4.35);
    tl.to({}, { duration: 0.4 }, 4.8); // hold
  }

  loadEngine().then((e) => {
    engine = e;
    window.gsap?.registerPlugin(window.ScrollTrigger);
    build();
    // Rebuild on real width changes (not on mobile URL-bar height changes).
    let t;
    window.addEventListener("resize", () => {
      if (Math.abs(window.innerWidth - lastWidth) < 40) return;
      lastWidth = window.innerWidth;
      clearTimeout(t);
      t = setTimeout(() => { build(); window.ScrollTrigger?.refresh(); }, 250);
    });
  }).catch(() => (msgEl.textContent = "The model did not load. Refresh to try again."));
}
