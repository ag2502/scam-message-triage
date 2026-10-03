// Scripted demo for the video. Everything on the stage is a pure function of time: renderAt(t).
// scripts/record_demo.py steps t frame by frame and encodes the frames; opened directly, it loops live.
import { Engine } from "./engine.js";
import { esc, LEVEL_LABEL } from "./ui.js";

const $ = (s) => document.querySelector(s);
const clamp = (v) => Math.min(1, Math.max(0, v));
const ease = (p) => 1 - Math.pow(1 - clamp(p), 3); // easeOutCubic
const inOut = (p) => { p = clamp(p); return p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2; };
const prog = (t, start, dur) => ease((t - start) / dur);
const win = (t, a, b, f = 0.35) => Math.min(prog(t, a, f), 1 - prog(t, b - f, f)); // fade in at a, out at b

const SCAM = "Hi Mum, I dropped my phone so this is my new number 🙏 Can you send R$800 by Pix today? It's urgent and I can't talk right now";
const TOLL = "E-ZPass: you have an unpaid toll of $6.89. Pay now to avoid a $50 late fee: ezpass-tollpay.vip";
const LEGIT = "Nubank: you sent a Pix of R$120.00 to Ana Souza.";

export const DURATION = 49;
export const CHAPTERS = [
  { t: 0, title: "Intro" },
  { t: 3.2, title: "A 'new number' asks for a Pix" },
  { t: 11, title: "Forward it to the bot" },
  { t: 17.5, title: "The verdict, in about a second" },
  { t: 25.5, title: "Fake fees and look-alike links" },
  { t: 32, title: "Real messages pass" },
  { t: 38, title: "Or check it on the web" },
  { t: 44.5, title: "Wrap-up" },
];
const CAPTIONS = [
  [3.2, 11, "ph-warning", "Unknown number", "A 'new number' asks for money", "It sounds like family, it's urgent, and it wants a Pix right now."],
  [11, 17.5, "ph-share-fat", "No app needed", "Long-press, then forward", "Send it to the Scam Triage bot like any other message. Nothing to install."],
  [17.5, 25.5, "ph-seal-warning", "Real model output", "The verdict, in about a second", "High risk: a fake relative. The reply says why, and what to do next."],
  [25.5, 32, "ph-link-break", "Links and fees", "Fake fees and look-alike links", "A toll notice with a look-alike domain gets flagged too."],
  [32, 38, "ph-check-circle", "Low false alarms", "Real messages pass", "A genuine Pix receipt scores low, so warnings keep their meaning."],
  [38, 44.5, "ph-browser", "On the web", "Or paste it on the site", "The same model runs in your browser. Nothing you paste is uploaded."],
];

const time = "09:41";
function botHtml(r) {
  const emoji = { high: "🔴", medium: "🟠", low: "🟢" }[r.risk_level];
  const why = r.reasons.slice(0, 2).map((x) => `<li>${esc(x)}</li>`).join("");
  // No newlines inside: bubbles use white-space: pre-line.
  return `<span class="bubble__badge">${emoji} ${LEVEL_LABEL[r.risk_level]} (${Math.round(r.risk_score * 100)}%)</span><br>` +
    `<b>${esc(r.scam_type_label)}${r.risk_level === "low" ? "." : ""}</b>${why ? `<ul>${why}</ul>` : ""}` +
    `${r.next_steps[0] ? `<b>Next:</b> ${esc(r.next_steps[0])}` : ""}<span class="bubble__time">${time}</span>`;
}

function message(body, cls, html, show, hide = Infinity) {
  const m = document.createElement("div");
  m.className = "m";
  m.innerHTML = `<div class="${cls}">${html}</div>`;
  body.append(m);
  return { el: m, show, hide, h: 0 };
}

let items = [];
let refs = {};

async function setup() {
  const engine = await Engine.load(new URL("../model/en.json", import.meta.url));
  const [rScam, rToll, rLegit] = [SCAM, TOLL, LEGIT].map((t) => engine.triage(t));
  const a = $("[data-body-a]"), b = $("[data-body-b]");
  const out = (text) => `<span class="bubble__fwd"><i class="ph ph-share-fat"></i>Forwarded</span>${esc(text)}<span class="bubble__time">${time}</span>`;
  const typing = "<i></i><i></i><i></i>";
  items = [
    message(a, "typing", typing, 4.2, 5.6),
    message(a, "bubble bubble--in", `${esc(SCAM)}<span class="bubble__time">${time}</span>`, 5.6),
    message(b, "bubble bubble--out", out(SCAM), 17.8),
    message(b, "typing", typing, 18.5, 19.7),
    message(b, "bubble bubble--in", botHtml(rScam), 19.7),
    message(b, "bubble bubble--out", out(TOLL), 25.8),
    message(b, "typing", typing, 26.5, 27.6),
    message(b, "bubble bubble--in", botHtml(rToll), 27.6),
    message(b, "bubble bubble--out", out(LEGIT), 32.3),
    message(b, "typing", typing, 33.0, 34.0),
    message(b, "bubble bubble--in", botHtml(rLegit), 34.0),
  ];
  await document.fonts.ready;
  items.forEach((it) => (it.h = it.el.scrollHeight));

  $("[data-captions]").innerHTML = CAPTIONS.map(([, , icon, k, h, p]) =>
    `<div class="cap"><span class="k"><i class="ph ${icon}"></i>${esc(k)}</span><h2>${esc(h)}</h2><p>${esc(p)}</p></div>`).join("");
  refs = {
    caps: [...document.querySelectorAll(".cap")],
    chatA: $("[data-chat-a]"), chatB: $("[data-chat-b]"), menu: $("[data-menu]"), menuFwd: $("[data-menu-fwd]"),
    sheet: $("[data-sheet]"), bot: $("[data-bot-contact]"), send: $("[data-send]"), tap: $("[data-tap]"),
    phone: $("[data-phone]"), browser: $("[data-browser]"), title: $("[data-title]"), end: $("[data-end]"),
    progress: $("[data-progress]"), statusA: $("[data-status-a]"), statusB: $("[data-status-b]"),
    scamBubble: items[1].el.firstElementChild, screen: document.querySelector(".screen"),
  };
}

function tapAt(el, t, at) {
  // A tap ripple centred on `el`, visible for 0.5 s from `at`.
  const p = (t - at) / 0.5;
  if (p < 0 || p > 1) return false;
  const s = refs.screen.getBoundingClientRect(), r = el.getBoundingClientRect();
  refs.tap.style.left = `${r.left - s.left + r.width / 2}px`;
  refs.tap.style.top = `${r.top - s.top + r.height / 2}px`;
  refs.tap.style.opacity = String(1 - p);
  refs.tap.style.transform = `scale(${0.6 + p * 0.8})`;
  return true;
}

export function renderAt(t) {
  // Chat messages grow in from height 0, so older ones slide up naturally.
  for (const it of items) {
    const p = Math.min(prog(t, it.show, 0.45), 1 - prog(t, it.hide, 0.2));
    it.el.style.height = `${it.h * p}px`;
    it.el.style.opacity = String(p);
    it.el.firstElementChild.style.transform = `translateY(${(1 - p) * 10}px)`;
  }
  refs.statusA.textContent = t > 4.2 && t < 5.6 ? "typing..." : "online";
  refs.statusB.textContent = [[18.5, 19.7], [26.5, 27.6], [33, 34]].some(([a, b]) => t > a && t < b) ? "typing..." : "online";

  // Long-press -> menu -> forward sheet -> select bot -> send -> switch to bot chat
  const press = prog(t, 11.6, 0.4) * (1 - prog(t, 12.6, 0.3));
  refs.scamBubble.style.transform = `scale(${1 - press * 0.03})`;
  refs.scamBubble.style.filter = `brightness(${1 - press * 0.08})`;
  const menu = win(t, 12.2, 13.5, 0.25);
  refs.menu.style.opacity = String(menu);
  if (menu > 0) {
    const sr = refs.screen.getBoundingClientRect(), br = refs.scamBubble.getBoundingClientRect();
    refs.menu.style.top = `${br.top - sr.top - refs.menu.offsetHeight - 10}px`;
  }
  refs.menu.style.transform = `scale(${0.92 + menu * 0.08})`;
  refs.menuFwd.classList.toggle("on", t > 12.9);
  const sheet = prog(t, 13.5, 0.5) * (1 - prog(t, 17, 0.3));
  refs.sheet.style.transform = `translateY(${(1 - sheet) * 110}%)`;
  refs.bot.classList.toggle("sel", t > 15.0);
  const tapping = tapAt(refs.scamBubble, t, 11.5) || tapAt(refs.menuFwd, t, 12.95) || tapAt(refs.bot, t, 14.9) || tapAt(refs.send, t, 16.2);
  if (!tapping) refs.tap.style.opacity = "0";
  const toB = inOut((t - 17) / 0.5);
  refs.chatA.style.opacity = String(1 - toB);
  refs.chatB.style.opacity = String(toB);
  refs.chatA.style.transform = `translateX(${-toB * 30}%)`;
  refs.chatB.style.transform = `translateX(${(1 - toB) * 30}%)`;

  // Phone out, browser in for the web scene
  const web = prog(t, 38, 0.7);
  refs.phone.style.transform = `translateX(${-web * 140}px)`;
  refs.phone.style.opacity = String(1 - web);
  refs.browser.style.opacity = String(web);
  refs.browser.style.transform = `translateY(${(1 - web) * 40}px) scale(${0.96 + web * 0.04})`;

  // Captions
  CAPTIONS.forEach(([a, b], i) => {
    const p = win(t, a + 0.2, b, 0.45);
    refs.caps[i].style.opacity = String(p);
    refs.caps[i].style.transform = `translateY(calc(-50% + ${(1 - p) * 18}px))`;
  });

  // Title and end cards
  const title = 1 - prog(t, 2.7, 0.5);
  refs.title.style.opacity = String(title);
  refs.title.style.transform = `scale(${1 + (1 - title) * 0.04})`;
  const end = prog(t, 44.5, 0.6);
  refs.end.style.opacity = String(end);
  refs.end.style.transform = `scale(${0.97 + end * 0.03})`;
  refs.progress.style.width = `${(t / DURATION) * 100}%`;
}

window.demo = { renderAt, DURATION, CHAPTERS, ready: setup().then(() => renderAt(0)) };

// Live playback when the page is opened directly (the recorder sets ?record).
if (!new URLSearchParams(location.search).has("record")) {
  window.demo.ready.then(() => {
    const t0 = performance.now();
    const loop = (now) => { renderAt(((now - t0) / 1000) % DURATION); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  });
}
