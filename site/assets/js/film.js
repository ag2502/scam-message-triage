// Cinematic product film. Every frame is a pure function of time: renderAt(t).
// scripts/record_demo.py --page film.html steps it frame by frame, synthesizes the soundtrack
// from CUES/MUSIC and encodes MP4 + WebM. Opened directly, it plays live (silently) in a loop.
import { Engine } from "./engine.js";
import { esc, LEVEL_LABEL, LEVEL_ICON } from "./ui.js";
import { signalName } from "./checker.js";
import { pickSignals, messageHtml } from "./story.js";

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const cl = (v) => Math.min(1, Math.max(0, v));
const p = (t, a, d) => cl((t - a) / d);
const eo = (x) => 1 - Math.pow(1 - cl(x), 3);
const eio = (x) => { x = cl(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const spring = (x) => { x = cl(x); return x === 0 ? 0 : 1 - Math.cos(x * Math.PI * 2.2) * Math.exp(-x * 5.5); };
const lerp = (a, b, x) => a + (b - a) * x;
const win = (t, a, b, f = 0.4) => Math.min(eo(p(t, a, f)), 1 - eo(p(t, b - f, f)));
const css = (el, o) => Object.assign(el.style, o);

const SCAM = "Hi Mum, I dropped my phone so this is my new number 🙏 Can you send R$800 by Pix today? It's urgent and I can't talk right now";
const MONTAGE = [
  ["Fake toll fine", "E-ZPass: you have an unpaid toll of $6.89. Pay now to avoid a $50 late fee: ezpass-tollpay.vip"],
  ["Fake parcel fee", "Royal Mail: your parcel is on hold due to an unpaid £1.99 redelivery fee. Pay within 24 hours: royalmail-redelivery.top/pay"],
  ["Stolen code", "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?"],
];
const LEGIT = ["A real receipt", "Nubank: you sent a Pix of R$120.00 to Ana Souza."];

export const DURATION = 72;
export const CHAPTERS = [
  { t: 0, title: "A message from a 'new number'" },
  { t: 7, title: "The pressure" },
  { t: 14, title: "Forward it to the bot" },
  { t: 22, title: "Inside the model" },
  { t: 34, title: "The reply, in plain words" },
  { t: 40.5, title: "Fake fines, fees and codes" },
  { t: 47, title: "Real messages pass" },
  { t: 50.5, title: "WhatsApp, web, API, banks" },
  { t: 60, title: "Honest results" },
  { t: 66, title: "Forward. Check. Then pay." },
];
const SUBS = [
  [0.8, 6.7, "9:41 on a Saturday. A message from a number you don't know."],
  [14.2, 21.4, "Don't reply. Long-press it and forward it to Scam Triage."],
  [22.6, 27.9, "It finds the phrases scammers rely on..."],
  [28.1, 33.4, "...weighs each one, and scores the risk. All on your device."],
  [34.6, 40.3, "The answer comes back in about a second, in plain words."],
  [41.2, 46.2, "Fake toll fines. Parcel fees. Stolen codes."],
  [47.2, 50.3, "Real messages pass, so the warnings keep their meaning."],
  [60.4, 65.6, "Tested honestly, on messages it had never seen."],
];
// Sound cues for the soundtrack synthesizer (scripts/film_audio.py).
export const CUES = [
  [1.2, "notif"], [1.25, "buzz"], [1.95, "buzz"],
  [7.6, "thump"], [8.7, "thump"], [9.8, "thump"], [10.9, "thump"], [12.3, "whoosh"], [12.4, "impact"],
  [14.5, "tap"], [15.8, "tap"], [17.15, "tap"], [17.5, "whoosh"], [18.6, "tap"], [19.4, "tap"], [20.6, "send"],
  [21.6, "whoosh"],
  [23.4, "tick"], [23.9, "tick"], [24.4, "tick"], [24.9, "tick"], [25.4, "pop"], [25.85, "pop"], [26.3, "pop"], [26.75, "pop"], [27.2, "pop"],
  [28.4, "riser"], [30.8, "impact"], [33.6, "whoosh"],
  [35.1, "receive"], [36.7, "tap"], [37.0, "send"], [38.1, "receive"],
  [40.5, "whoosh"], [42.6, "pop"], [43.6, "pop"], [44.6, "pop"], [46.2, "whoosh"], [48.2, "chime"],
  [50.9, "whoosh"], [52.5, "whoosh"], [52.8, "typing:1.8"], [56.2, "whoosh"], [56.9, "whoosh"],
  [60.6, "riser_short"], [61.8, "impact"], [62.2, "pop"],
  [66.5, "impact"], [67.0, "thump"], [67.4, "thump"], [67.8, "thump"], [68.6, "chime_end"],
];
// Music arrangement: which layers play when (seconds).
export const MUSIC = { bpm: 96, pad: [[0, 72]], pulse: [[7, 22], [30.8, 60]], kick: [[14, 22], [30.8, 60]], bass: [[7, 66]], riser: [[28.4, 30.8]], outro: [[66, 72]] };

let R = {}; // DOM refs + precomputed data

function msg(body, rowCls, html, show, hide = Infinity) {
  const m = document.createElement("div");
  m.className = "m";
  m.innerHTML = `<div class="wa-row ${rowCls}">${html}</div>`;
  body.append(m);
  return { el: m, show, hide, h: 0 };
}
const verdictHtml = (r, steps = false) => `<div class="wa-b wa-b--in"><div class="wa-verdict lvl-${r.risk_level}">
    <span class="badge"><i class="${LEVEL_ICON[r.risk_level]}"></i>${LEVEL_LABEL[r.risk_level]} ${Math.round(r.risk_score * 100)}%</span>
    <strong>${esc(r.scam_type_label)}</strong>
    ${r.risk_level === "low" ? `<p>${esc(r.summary)}</p>` : `<ul>${r.reasons.slice(0, 2).map((x) => `<li>${esc(x)}</li>`).join("")}</ul>${steps ? "" : `<p><b>Next:</b> ${esc(r.next_steps[0])}</p>`}`}
  </div><span class="wa-meta">9:42</span></div>`;
const outHtml = (text, fwd = true) => `<div class="wa-b wa-b--out">${fwd ? '<span class="wa-fwd"><i class="ph ph-share-fat"></i>Forwarded</span>' : ""}${esc(text)}<span class="wa-meta">9:42 <i class="ph ph-checks is-read"></i></span></div>`;
const typingHtml = '<div class="typing"><i></i><i></i><i></i></div>';

async function setup() {
  const engine = await Engine.load(new URL("../model/en.json", import.meta.url));
  engine.triage(SCAM);
  const r = engine.triage(SCAM);
  const ms = r.extras.ms;
  $("[data-notif-text]").textContent = SCAM.slice(0, 92) + "...";

  // Chat A (unknown number)
  const bodyA = $("[data-body-a]");
  const scamRow = msg(bodyA, "wa-row--in", `<div class="wa-b wa-b--in">${esc(SCAM)}<span class="wa-meta">9:41</span></div>`, -1);
  // Chat B (bot)
  const bodyB = $("[data-body-b]");
  const btns = `<div class="wa-btns"><button type="button"><i class="ph ph-question"></i>Why?</button><button type="button" data-todo><i class="ph ph-list-checks"></i>What should I do?</button></div>`;
  const items = [
    scamRow,
    msg(bodyB, "wa-row--out", outHtml(SCAM), 20.6),
    msg(bodyB, "wa-row--in", typingHtml, 34.4, 35.1),
    msg(bodyB, "wa-row--in", verdictHtml(r) + btns, 35.1),
    msg(bodyB, "wa-row--out", outHtml("What should I do?", false), 37.0),
    msg(bodyB, "wa-row--in", typingHtml, 37.3, 38.1),
    msg(bodyB, "wa-row--in", `<div class="wa-b wa-b--in"><b>What to do:</b><ol class="wa-list wa-list--num">${r.next_steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol><span class="wa-meta">9:42</span></div>`, 38.1),
  ];

  // Analysis scene, built from the real triage
  const ana = $("[data-ana]");
  const picks = pickSignals(engine, SCAM, r);
  $("[data-ana-msg]").innerHTML = messageHtml(SCAM, picks);
  $("[data-ana-slots]").innerHTML = picks.map((pk, i) => `<li class="slot" data-slot="${i}"><span class="slot__empty">signal ${i + 1}</span>
      <span class="slot__full"><i class="ph-fill ph-flag"></i><span class="slot__name">${esc(signalName(pk.id))}</span><span class="slot__num">+${pk.w.toFixed(2)}</span></span></li>`).join("");
  const ARC = Math.PI * 70;
  $("[data-ana-gauge]").innerHTML = `<svg viewBox="0 0 160 96"><path class="gauge__track" d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke-width="12" stroke-linecap="round"/>
      <path class="gauge__value" data-arc d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke="var(--lvl)" stroke-width="12" stroke-linecap="round" stroke-dasharray="${ARC}"/>
      <text class="gauge__num" x="80" y="74" text-anchor="middle" data-num>0%</text><text class="gauge__cap" x="80" y="92" text-anchor="middle">RISK SCORE</text></svg>`;
  $("[data-ana-verdict]").innerHTML = `<span class="badge"><i class="${LEVEL_ICON[r.risk_level]}"></i>${LEVEL_LABEL[r.risk_level]}</span>
      <h3>${esc(r.scam_type_label)}</h3><p>${esc(r.next_steps[0])}</p><small class="mono" style="color:var(--muted)">Computed in ${ms.toFixed(1)} ms on this device.</small>`;

  // Montage phones
  const mont = $("[data-mont]");
  const montage = [...MONTAGE, LEGIT].map(([label, text], i) => {
    const res = engine.triage(text);
    const el = document.createElement("div");
    el.className = "mphone";
    el.innerHTML = `<div class="mphone__screen"><div class="wa-row wa-row--out">${outHtml(text)}</div><div class="wa-row wa-row--in" data-mv>${verdictHtml(res, true)}</div></div><span class="mphone__label lvl-${res.risk_level}">${esc(label)}</span>`;
    mont.append(el);
    return { el, v: $("[data-mv]", el), label: $(".mphone__label", el), i };
  });

  // API code text (real response values)
  const apiResp = { risk_score: r.risk_score, risk_level: r.risk_level, scam_type: r.scam_type, reasons: r.reasons.slice(0, 2) };
  R.code = [
    ["c", "$ "], ["k", "curl"], ["", " -X POST https://your-host/v1/triage \\\n    -d '"], ["s", `{"text": "Hi Mum, new number..."}`], ["", "'\n\n"],
    ["", JSON.stringify(apiResp, null, 2)],
  ];
  R.codeLen = R.code.reduce((n, [, s]) => n + s.length, 0);

  await document.fonts.ready;
  items.forEach((it) => (it.h = it.el.scrollHeight));

  // Fly clones for the analysis (measured relative to the analysis layer, at rest)
  const ar = ana.getBoundingClientRect();
  const box = (el) => { const b = el.getBoundingClientRect(); return { x: b.left - ar.left, y: b.top - ar.top, w: b.width, h: b.height }; };
  const msgFont = getComputedStyle($("[data-ana-msg]")).fontSize;
  R.flies = picks.map((pk, i) => {
    const ev = $(`[data-ev="${i}"]`, ana);
    if (!ev) return null;
    const from = box(ev), to = box($(`[data-slot="${i}"]`, ana));
    const k = Math.min((to.h * 0.6) / from.h, (to.w - 70) / from.w, 1);
    const fly = document.createElement("span");
    fly.className = "fly";
    fly.textContent = ev.textContent.replace(signalName(pk.id), "").trim();
    css(fly, { left: `${from.x}px`, top: `${from.y}px`, width: `${from.w}px`, height: `${from.h}px`, fontSize: msgFont, transformOrigin: "0 0" });
    ana.append(fly);
    return { fly, dx: to.x + 42 - from.x, dy: to.y + (to.h - from.h * k) / 2 - from.y, k };
  });

  Object.assign(R, {
    r, ms, items, montage, ARC,
    stage: $("[data-stage]"), persp: $("[data-persp]"), phone: $("[data-phone]"), screen: $("[data-screen]"),
    lock: $("[data-lock]"), notif: $("[data-notif]"), chatA: $("[data-chat-a]"), chatB: $("[data-chat-b]"),
    menu: $("[data-menu]"), menuFwd: $("[data-menu-fwd]"), sheet: $("[data-sheet]"), bot: $("[data-bot-contact]"), send: $("[data-send]"),
    tap: $("[data-tap]"), statusB: $("[data-status-b]"), todoBtn: $("[data-todo]", items[3].el),
    kin: $("[data-kin]"), kl: $$("[data-kl]"), kfinal: $("[data-kfinal]"),
    ana, anaLabel: $("[data-ana-label]"), words: $$(".w", ana), evs: $$(".ev", ana), tags: $$(".ev__tag", ana),
    slotsFull: $$(".slot__full", ana), slots: $$(".slot", ana), arc: $("[data-arc]"), num: $("[data-num]"), verdict: [...$("[data-ana-verdict]").children],
    every: $("[data-every]"), evWeb: $("[data-ev-web]"), evApi: $("[data-ev-api]"), evBank: $("[data-ev-bank]"), evChat: $("[data-ev-chat]"), evCode: $("[data-ev-code]"),
    fstats: $("[data-fstats]"), fs1: $("[data-fs1]"), fs2: $("[data-fs2]"), fs1n: $("[data-fs1-num]"), fs2n: $("[data-fs2-num]"), fsNote: $("[data-fs-note]"), fsMs: $("[data-fs-ms]"),
    end: $("[data-end]"), endMark: $("[data-end-mark]"), endWords: $$("[data-end-h] span"), endUrl: $("[data-end-url]"), endFoot: $("[data-end-foot]"),
    subs: $("[data-subs]"), glowA: $("[data-glow-a]"), glowB: $("[data-glow-b]"),
  });
  R.fsMs.textContent = `Each check: about ${Math.max(1, Math.round(ms))} ms, on your device.`;
}

function tapAt(el, t, at) {
  const k = (t - at) / 0.45;
  if (k < 0 || k > 1) return false;
  const s = R.screen.getBoundingClientRect(), b = el.getBoundingClientRect();
  const sc = s.width / R.screen.offsetWidth || 1; // screen may be scaled by the camera
  css(R.tap, { left: `${(b.left - s.left + b.width / 2) / sc}px`, top: `${(b.top - s.top + b.height / 2) / sc}px`, opacity: String(1 - k), transform: `scale(${0.55 + k * 0.8})` });
  return true;
}

export function renderAt(t) {
  // ---- ambient glows
  css(R.glowA, { transform: `translate(${Math.sin(t * 0.21) * 60}px, ${Math.cos(t * 0.17) * 40}px)` });
  css(R.glowB, { transform: `translate(${Math.cos(t * 0.19) * 70}px, ${Math.sin(t * 0.23) * 50}px)` });

  // ---- phone placement across scenes
  const toSide = eio(p(t, 7, 0.8)) * (1 - eio(p(t, 14, 0.8)));
  const dive = eio(p(t, 21.6, 0.8)) * (1 - eio(p(t, 33.6, 0.8)));
  const exit = eio(p(t, 40.5, 0.7));
  const vib = (t > 1.2 && t < 1.8) || (t > 1.95 && t < 2.5) ? Math.sin(t * 95) * 4 : 0;
  const ry = t < 7 ? lerp(-18, -8, eo(p(t, 0, 7))) : lerp(-8, 0, eio(p(t, 14, 0.8))) + toSide * 30 + (t > 34 ? Math.sin(t * 0.7) * 5 : 0);
  const rx = t < 14 ? 6 : lerp(6, 2, eo(p(t, 14, 1)));
  const zoom = 0.88 * (t < 7 ? lerp(1, 1.1, eo(p(t, 0, 7))) : lerp(1.1, 1, eo(p(t, 7, 0.8)))) * lerp(1, 3.4, dive) * lerp(1, 0.55, exit);
  css(R.persp, {
    transform: `translate(${-340 * toSide + vib}px, ${-60 * exit}px) scale(${zoom})`,
    opacity: String(Math.min(1 - eio(p(t, 21.9, 0.5)) + eio(p(t, 33.6, 0.6)), 1) * (1 - exit) * (t > 33.6 || t < 22.4 ? 1 : 0)),
    filter: toSide > 0.01 ? `brightness(${1 - toSide * 0.35})` : "none",
  });
  css(R.phone, { transform: `rotateY(${ry}deg) rotateX(${rx}deg)` });

  // ---- inside the phone: lock -> chat A -> chat B
  const notifIn = spring(p(t, 1.2, 1.1));
  css(R.notif, { transform: `translateY(${lerp(-170, 0, notifIn)}px) scale(${lerp(0.9, 1, cl(notifIn))})`, opacity: String(cl(p(t, 1.2, 0.25))) });
  const toA = eio(p(t, 14.9, 0.45));
  css(R.lock, { opacity: String(1 - toA), transform: `scale(${1 + toA * 0.08})` });
  const toB = eio(p(t, 19.9, 0.5));
  css(R.chatA, { opacity: String(toA * (1 - toB)), transform: `translateX(${-30 * toB}%)` });
  css(R.chatB, { opacity: String(toB), transform: `translateX(${30 * (1 - toB)}%)` });
  for (const it of R.items) {
    const k = it.show < 0 ? 1 : Math.min(eo(p(t, it.show, 0.45)), 1 - eo(p(t, it.hide, 0.2)));
    css(it.el, { height: `${it.h * k}px`, opacity: String(k) });
  }
  R.statusB.textContent = (t > 34.4 && t < 35.1) || (t > 37.3 && t < 38.1) ? "typing..." : "online";
  const press = eo(p(t, 15.8, 0.35)) * (1 - eo(p(t, 16.6, 0.3)));
  const sb = R.items[0].el.querySelector(".wa-b");
  css(sb, { transform: `scale(${1 - press * 0.035})`, filter: `brightness(${1 - press * 0.12})` });
  const menu = win(t, 16.3, 17.5, 0.25);
  if (menu > 0) {
    const s = R.screen.getBoundingClientRect(), b = sb.getBoundingClientRect(), sc = s.width / R.screen.offsetWidth || 1;
    css(R.menu, { top: `${(b.top - s.top) / sc - R.menu.offsetHeight - 10}px` });
  }
  css(R.menu, { opacity: String(menu), transform: `scale(${0.9 + menu * 0.1})` });
  R.menuFwd.classList.toggle("on", t > 17.1);
  const sheet = eo(p(t, 17.5, 0.5)) * (1 - eo(p(t, 19.8, 0.3)));
  css(R.sheet, { transform: `translateY(${(1 - sheet) * 110}%)` });
  R.bot.classList.toggle("sel", t > 18.65);
  R.todoBtn.classList.toggle("is-picked", t > 36.8);
  const tapping = tapAt(R.notif, t, 14.5) || tapAt(sb, t, 15.8) || tapAt(R.menuFwd, t, 17.15) || tapAt(R.bot, t, 18.6) || tapAt(R.send, t, 19.4) || tapAt(R.todoBtn, t, 36.7);
  if (!tapping) R.tap.style.opacity = "0";

  // ---- kinetic type
  css(R.kin, { opacity: String(win(t, 7.3, 13.9, 0.4)) });
  R.kl.forEach((el, i) => {
    const at = 7.6 + i * 1.1;
    const k = spring(p(t, at, 0.7));
    const out = eo(p(t, 12.2, 0.4));
    css(el, { opacity: String(cl(p(t, at, 0.12)) * (1 - out)), transform: `scale(${lerp(1.45, 1, cl(k))}) translateX(${out * -40}px)`, filter: `blur(${(1 - cl(p(t, at, 0.25))) * 10}px)` });
  });
  const fin = spring(p(t, 12.4, 0.8));
  css(R.kfinal, { opacity: String(cl(p(t, 12.4, 0.2))), transform: `scale(${lerp(1.6, 1, cl(fin))})` });

  // ---- analysis
  const anaOn = Math.min(eo(p(t, 22.1, 0.5)), 1 - eo(p(t, 33.5, 0.5)));
  css(R.ana, { opacity: String(anaOn), transform: `scale(${lerp(0.94, 1, anaOn)})`, visibility: anaOn > 0 ? "visible" : "hidden" });
  R.words.forEach((w, i) => {
    const k = eo(p(t, 22.4 + (i / R.words.length) * 0.8, 0.2));
    const dim = w.closest(".ev") ? 0 : eo(p(t, 25.2, 0.4)) * 0.68;
    css(w, { opacity: String(k * (1 - dim)), transform: `translateY(${(1 - k) * 14}px)` });
  });
  R.evs.forEach((ev, i) => { css(ev, { backgroundSize: `${eo(p(t, 23.4 + i * 0.5, 0.35)) * 100}% 100%` }); });
  R.tags.forEach((tag, i) => { const k = spring(p(t, 23.5 + i * 0.5, 0.5)); css(tag, { opacity: String(cl(p(t, 23.5 + i * 0.5, 0.15))), transform: `translateY(${(1 - cl(k)) * 8}px) scale(${lerp(0.7, 1, cl(k))})` }); });
  R.flies.forEach((f, i) => {
    const at = 25.4 + i * 0.45;
    const full = R.slotsFull[i];
    if (f) {
      const k = eio(p(t, at, 0.7));
      css(f.fly, { opacity: String(t < at ? 0 : 1 - eo(p(t, at + 0.65, 0.15))), transform: `translate(${f.dx * k}px, ${f.dy * k}px) scale(${lerp(1, f.k, k)})` });
    }
    css(full, { opacity: String(eo(p(t, at + (f ? 0.6 : 0.1), 0.15))) });
  });
  const g = eio(p(t, 28.4, 2));
  R.arc.style.strokeDashoffset = String(R.ARC * (1 - R.r.risk_score * g));
  R.num.textContent = `${Math.round(R.r.risk_score * 100 * g)}%`;
  R.slots.forEach((s, i) => { const k = Math.sin(cl(p(t, 28.4 + i * 0.12, 0.35)) * Math.PI); css(s, { transform: `scale(${1 + k * 0.05})` }); });
  R.verdict.forEach((el, i) => { const k = spring(p(t, 30.8 + i * 0.12, 0.7)); css(el, { opacity: String(cl(p(t, 30.8 + i * 0.12, 0.15))), transform: `scale(${lerp(1.35, 1, cl(k))})`, transformOrigin: "0 50%" }); });
  css(R.anaLabel, { opacity: String(anaOn) });

  // ---- montage
  R.montage.forEach(({ el, v, label, i }) => {
    const legit = i === 3;
    const enter = legit ? spring(p(t, 46.8, 1.0)) : spring(p(t, 41 + i * 0.35, 1.1));
    const leave = legit ? eo(p(t, 50.2, 0.5)) : eo(p(t, 46.2, 0.5));
    const x = legit ? 0 : [-370, 0, 370][i], rY = legit ? 0 : [24, 0, -24][i], z = legit ? 60 : [-80, 40, -80][i];
    const vis = legit ? (t > 46.6) : (t > 40.8);
    css(el, {
      opacity: String(vis ? cl(enter) * (1 - leave) : 0),
      transform: `translate3d(${x}px, ${lerp(520, 0, cl(enter)) - leave * 60}px, ${z}px) rotateY(${rY}deg) rotateX(${lerp(28, 4, cl(enter))}deg) scale(${1 - leave * 0.15})`,
    });
    const vAt = legit ? 48.2 : 42.6 + i * 1.0;
    const vk = spring(p(t, vAt, 0.6));
    css(v, { opacity: String(cl(p(t, vAt, 0.12))), transform: `scale(${lerp(0.7, 1, cl(vk))})`, transformOrigin: "0 100%" });
    css(label, { opacity: String(cl(p(t, vAt + 0.1, 0.3)) * (1 - leave)) });
  });

  // ---- everywhere
  const evOut = eo(p(t, 59.6, 0.6));
  const panel = (el, at, fromX, rot) => { const k = spring(p(t, at, 1.0)); css(el, { opacity: String(cl(p(t, at, 0.25)) * (1 - evOut)), transform: `perspective(1400px) translateX(${lerp(fromX, 0, cl(k))}px) rotateY(${lerp(rot, rot * 0.3, cl(k))}deg)` }); };
  css(R.every, { visibility: t > 50.5 && t < 60.4 ? "visible" : "hidden" });
  panel(R.evWeb, 50.9, -120, 14);
  panel(R.evApi, 52.5, 120, -12);
  panel(R.evChat, 56.2, 80, -10);
  panel(R.evBank, 56.9, 120, -12);
  const typed = Math.floor(R.codeLen * cl(p(t, 52.8, 1.8)));
  const shown = Math.floor(R.codeLen * cl(p(t, 52.8, 1.8)) + (t > 54.8 ? R.codeLen : 0));
  let left = Math.max(typed, Math.min(shown, R.codeLen)), html = "";
  for (const [cls, s] of R.code) { if (left <= 0) break; const part = s.slice(0, left); left -= part.length; html += cls ? `<span class="${cls}">${esc(part)}</span>` : esc(part); }
  R.evCode.innerHTML = html + (t < 54.8 && Math.floor(t * 3) % 2 ? "▍" : "");

  // ---- stats
  const stOn = Math.min(eo(p(t, 60.2, 0.5)), 1 - eo(p(t, 65.6, 0.5)));
  css(R.fstats, { opacity: String(stOn), visibility: stOn > 0 ? "visible" : "hidden" });
  R.fs1n.textContent = String(Math.round(26 * eio(p(t, 60.6, 1.2))));
  const s1 = spring(p(t, 60.5, 0.8)), s2 = spring(p(t, 61.9, 0.8));
  css(R.fs1, { transform: `scale(${lerp(0.85, 1, cl(s1))})`, opacity: String(cl(p(t, 60.5, 0.2))) });
  css(R.fs2, { transform: `scale(${lerp(1.3, 1, cl(s2))})`, opacity: String(cl(p(t, 61.9, 0.2))) });
  R.fs2n.textContent = "0";
  css(R.fsNote, { opacity: String(eo(p(t, 62.8, 0.5))) });
  css(R.fsMs, { opacity: String(eo(p(t, 63.6, 0.5))) });

  // ---- end card
  css(R.end, { opacity: String(eo(p(t, 66.1, 0.5))), visibility: t > 66 ? "visible" : "hidden" });
  const mk = spring(p(t, 66.5, 0.8));
  css(R.endMark, { transform: `scale(${cl(mk) * (1 + 0.04 * Math.sin(t * 3) * cl(p(t, 68, 1)))})` });
  R.endWords.forEach((w, i) => { const k = spring(p(t, 67 + i * 0.4, 0.7)); css(w, { opacity: String(cl(p(t, 67 + i * 0.4, 0.15))), transform: `scale(${lerp(1.5, 1, cl(k))})`, filter: `blur(${(1 - cl(p(t, 67 + i * 0.4, 0.25))) * 8}px)` }); });
  css(R.endUrl, { opacity: String(eo(p(t, 68.6, 0.5))), transform: `translateY(${(1 - eo(p(t, 68.6, 0.5))) * 14}px)` });
  css(R.endFoot, { opacity: String(eo(p(t, 69.1, 0.5))) });

  // ---- subtitles
  const sub = SUBS.find(([a, b]) => t >= a && t <= b);
  R.subs.textContent = sub ? sub[2] : "";
  R.subs.style.opacity = sub ? String(win(t, sub[0], sub[1], 0.25)) : "0";
}

window.film = { renderAt, DURATION, CHAPTERS, CUES, MUSIC, ready: setup().then(() => renderAt(0)) };

if (!new URLSearchParams(location.search).has("record")) {
  window.film.ready.then(() => {
    const t0 = performance.now();
    const loop = (now) => { renderAt(((now - t0) / 1000) % DURATION); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  });
}
