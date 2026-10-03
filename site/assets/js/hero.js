// Hero phone: forwards example messages to the "bot" and shows the real model's reply.
import { $, esc, reducedMotion, LEVEL_LABEL } from "./ui.js";

const SCRIPT = [
  "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now",
  "E-ZPass: you have an unpaid toll of $6.89. Pay now to avoid a $50 late fee: ezpass-tollpay.vip",
  "Nubank: you sent a Pix of R$120.00 to Ana Souza.",
  "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?",
];
const EMOJI = { high: "🔴", medium: "🟠", low: "🟢" };
const wait = (ms) => new Promise((r) => setTimeout(r, ms));

function now() {
  return new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function botBubble(r) {
  const head = `<span class="bubble__badge">${EMOJI[r.risk_level]} ${LEVEL_LABEL[r.risk_level]} (${Math.round(r.risk_score * 100)}%)</span>`;
  const type = r.risk_level === "low" ? `<b>${esc(r.scam_type_label)}.</b>` : `<b>${esc(r.scam_type_label)}</b>`;
  const why = r.reasons.slice(0, 2).map((x) => `<li>${esc(x)}</li>`).join("");
  const step = r.next_steps[0] ? `<br><b>Next:</b> ${esc(r.next_steps[0])}` : "";
  return `${head}<br>${type}${why ? `<ul>${why}</ul>` : ""}${step}<span class="bubble__time">${now()}</span>`;
}

export function initHero({ loadEngine }) {
  const body = $("[data-hero-body]");
  const status = $("[data-hero-status]");
  const phone = $("[data-hero-phone]");
  if (!body) return;

  let visible = true;
  new IntersectionObserver(([e]) => (visible = e.isIntersecting)).observe(phone);

  const add = (cls, html) => {
    const el = document.createElement("div");
    el.className = cls;
    el.innerHTML = html;
    body.append(el);
    while (body.children.length > 4) body.firstElementChild.remove();
    return el;
  };

  const exchange = async (engine, text, animate) => {
    add("bubble bubble--out", `<span class="bubble__fwd"><i class="ph ph-share-fat"></i>Forwarded</span>${esc(text)}<span class="bubble__time">${now()}</span>`);
    if (animate) {
      await wait(700);
      status.textContent = "typing...";
      const typing = add("typing", "<i></i><i></i><i></i>");
      await wait(1300);
      typing.remove();
      status.textContent = "online";
    }
    add("bubble bubble--in", botBubble(engine.triage(text)));
  };

  (async () => {
    status.textContent = "typing...";
    const typing = add("typing", "<i></i><i></i><i></i>");
    let engine;
    try { engine = await loadEngine(); } catch { typing.remove(); status.textContent = "offline"; return; }
    typing.remove();
    status.textContent = "online";

    if (reducedMotion()) { await exchange(engine, SCRIPT[0], false); return; }
    for (let i = 0; ; i = (i + 1) % SCRIPT.length) {
      while (!visible || document.hidden) await wait(400);
      await exchange(engine, SCRIPT[i], true);
      await wait(3600);
    }
  })();
}
