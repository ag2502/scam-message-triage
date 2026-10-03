// The checker playground: paste a message, get an explained verdict.
import { $, esc, copy, toast, formatReply, b64urlEncode, b64urlDecode, LEVEL_ICON, LEVEL_LABEL } from "./ui.js";

export const SAMPLES = [
  { label: "Hi Mum, new number", text: "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now" },
  { label: "Pix sent by mistake", text: "Hi, I accidentally sent you R$450 by Pix, it was meant for my landlord. Could you please send it back to my key? I'm sending the receipt" },
  { label: "Bank fraud team", text: "Chase Fraud Alert: we blocked a payment of $1,940. To protect your savings, move your money to the safe account our agent gives you. Call +1 (415) 555 0182 now" },
  { label: "Parcel fee", text: "Royal Mail: your parcel is on hold due to an unpaid £1.99 redelivery fee. Pay within 24 hours: royalmail-redelivery.top/pay" },
  { label: "Code by mistake", text: "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?" },
  { label: "Task job", text: "Hi! Remote part-time job: like videos and earn ₹3,000 daily. To withdraw your commission, recharge ₹2,000 first" },
  { label: "Real Pix receipt", text: "Nubank: you sent a Pix of R$120.00 to Ana Souza.", legit: true },
  { label: "Real OTP", text: "Your WhatsApp code: 482-019. Don't share this code with others.", legit: true },
  { label: "Friend paying back", text: "Thanks for dinner! Just paid you back the $25 on Venmo 🙌", legit: true },
];

const SIGNAL_NAMES = {
  urgency: "urgency", money_request: "asks for money", payment_rail: "payment method", new_number: "new number",
  family_claim: "claims to be family", secrecy: "secrecy", avoid_voice: "avoids calls", code_request: "asks for a code",
  credential_request: "asks for credentials", account_threat: "account threat", safe_account: "safe account",
  remote_access: "remote access", refund_mistake: "sent by mistake", prize: "prize", fee_to_unlock: "fee to unlock",
  easy_income: "easy income", guaranteed_return: "guaranteed returns", authority: "authority", delivery: "delivery",
  bank_mention: "bank", has_link: "link", suspicious_link: "suspicious link", has_phone_number: "phone number",
  money_amount: "amount",
};
export const signalName = (id) => SIGNAL_NAMES[id] || id;

function gauge(score, level) {
  const len = Math.PI * 70;
  return `<div class="gauge"><svg viewBox="0 0 160 96" aria-hidden="true">
      <path class="gauge__track" d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke-width="12" stroke-linecap="round"/>
      <path class="gauge__value" d="M10 86 A70 70 0 0 1 150 86" fill="none" stroke="var(--lvl)" stroke-width="12" stroke-linecap="round"
        stroke-dasharray="${len}" stroke-dashoffset="${len}" data-target="${len * (1 - score)}"/>
      <text class="gauge__num" x="80" y="74" text-anchor="middle">${Math.round(score * 100)}%</text>
      <text class="gauge__cap" x="80" y="92" text-anchor="middle">RISK SCORE</text>
    </svg></div>`;
}

/** Highlight signal evidence (solid) and model key phrases (dotted) inside the original message. */
export function markText(text, r) {
  const ranges = [];
  const lower = text.toLowerCase();
  const addAll = (needle, cls, title) => {
    if (!needle || needle.length < 2) return;
    const n = needle.toLowerCase();
    let from = 0, i;
    while ((i = lower.indexOf(n, from)) !== -1) {
      const before = lower[i - 1], after = lower[i + n.length];
      const okEdge = cls !== "phrase" || ((!before || !/[\p{L}\p{N}]/u.test(before)) && (!after || !/[\p{L}\p{N}]/u.test(after)));
      if (okEdge) ranges.push([i, i + n.length, cls, title]);
      from = i + n.length;
    }
  };
  const reasonIds = new Set(r.extras.reason_ids);
  r.extras.signals.filter((s) => reasonIds.has(s.id)).forEach((s) => addAll(s.evidence, "sig", signalName(s.id)));
  r.key_phrases.filter((p) => !/\b0\b/.test(p)).forEach((p) => addAll(p, "phrase", "phrase the model weighed"));
  ranges.sort((a, b) => a[0] - b[0] || (a[2] === "sig" ? -1 : 1));
  let out = "", pos = 0;
  for (const [s, e, cls, title] of ranges) {
    if (s < pos) continue;
    out += esc(text.slice(pos, s)) + `<mark class="${cls === "phrase" ? "phrase" : ""}" title="${esc(title)}">${esc(text.slice(s, e))}</mark>`;
    pos = e;
  }
  return out + esc(text.slice(pos));
}

function renderResult(text, r, tax) {
  const lvl = r.risk_level;
  const typeProbs = Object.entries(r.extras.type_probs).sort((a, b) => b[1] - a[1]).slice(0, 5);
  const feats = r.extras.top_features.slice(0, 8);
  const maxC = Math.max(...feats.map((f) => Math.abs(f.contribution)), 0.001);
  const featName = (n) => n.startsWith("signal:") ? `signal: ${signalName(n.slice(7))}` : n.startsWith("char:") ? `chars "${n.slice(5)}"` : `"${n}"`;
  return `
    <div class="verdict lvl-${lvl}">
      ${gauge(r.risk_score, lvl)}
      <div>
        <span class="badge"><i class="${LEVEL_ICON[lvl]}"></i>${LEVEL_LABEL[lvl]}</span>
        <h3>${lvl === "low" ? esc(r.scam_type_label) : `Likely: ${esc(r.scam_type_label)}`}</h3>
        <p>${esc(lvl === "low" ? r.summary : tax[r.scam_type].description)}</p>
      </div>
    </div>
    ${r.reasons.length ? `<div class="block lvl-${lvl}"><h4>Why</h4><ul class="reasons">${r.reasons.map((x) => `<li><i class="ph-fill ph-flag"></i><span>${esc(x)}</span></li>`).join("")}</ul></div>` : ""}
    <div class="block lvl-${lvl}"><h4>Your message, annotated</h4>
      <p class="marked">${markText(text, r)}</p>
      <div class="legend"><span>warning sign</span>${r.key_phrases.length ? `<span class="dotted">phrase the model weighed</span>` : ""}</div>
    </div>
    <div class="block"><h4>What to do</h4><ul class="steps">${r.next_steps.map((x) => `<li><i class="ph ph-arrow-right"></i><span>${esc(x)}</span></li>`).join("")}</ul></div>
    <div class="result__actions">
      <button class="btn btn--ghost btn--sm" type="button" data-copy-reply><i class="ph ph-copy"></i>Copy WhatsApp reply</button>
      <button class="btn btn--ghost btn--sm" type="button" data-share><i class="ph ph-link-simple"></i>Share this check</button>
    </div>
    <details class="hood">
      <summary>Under the hood <i class="ph ph-caret-down"></i></summary>
      <div class="hood__grid">
        <div><h4 class="label">Scam type probabilities</h4>
          <ul class="bars">${typeProbs.map(([c, p]) => `<li><div><span class="name">${esc(tax[c].label)}</span><span class="bar" style="width:${Math.max(p * 100, 1.5)}%"></span></div><span class="val">${(p * 100).toFixed(1)}%</span></li>`).join("")}</ul>
        </div>
        <div><h4 class="label">Biggest pushes toward "scam"</h4>
          <ul class="bars">${feats.map((f) => `<li><div><span class="name mono">${esc(featName(f.name))}</span><span class="bar ${f.contribution < 0 ? "neg" : ""}" style="width:${Math.max(Math.abs(f.contribution) / maxC * 100, 1.5)}%"></span></div><span class="val">${f.contribution >= 0 ? "+" : ""}${f.contribution.toFixed(2)}</span></li>`).join("")}</ul>
        </div>
      </div>
      <h4 class="label">What the model actually reads</h4>
      <p class="pre">${esc(r.extras.preprocessed)}</p>
      <p class="help">${r.extras.n_features} active features, logit ${r.extras.logit.toFixed(2)}, computed in ${r.extras.ms.toFixed(1)} ms on your device.</p>
    </details>`;
}

export function initChecker({ state, loadEngine }) {
  const root = $("[data-checker]");
  if (!root) return;
  const form = $("[data-check-form]", root);
  const msg = $("[data-msg]", root);
  const btn = $("[data-check-btn]", root);
  const status = $("[data-model-status]", root);
  const views = { empty: $("[data-empty]", root), skeleton: $("[data-skeleton]", root), error: $("[data-error]", root), result: $("[data-result]", root) };
  const show = (name) => Object.entries(views).forEach(([k, el]) => (el.hidden = k !== name));
  let examples = [];

  // Sample chips
  const samples = $("[data-samples]", root);
  samples.innerHTML = SAMPLES.map((s, i) => `<button type="button" class="chip" data-sample="${i}">${s.legit ? '<i class="ph ph-check"></i>' : ""}${esc(s.label)}</button>`).join("");
  samples.addEventListener("click", (e) => {
    const b = e.target.closest("[data-sample]");
    if (!b) return;
    samples.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === b)));
    run(SAMPLES[+b.dataset.sample].text);
  });

  const ready = (engine) => {
    btn.disabled = false;
    status.innerHTML = `<i class="ph ph-lock-simple"></i>model v${esc(engine.m.version)} on-device`;
  };

  async function run(text) {
    text = (text ?? msg.value).trim();
    if (!text) { msg.focus(); toast("Paste a message first"); return; }
    msg.value = text;
    if (!state.engine) show("skeleton");
    let engine;
    try { engine = await loadEngine(); } catch (err) {
      $("[data-error-msg]", root).textContent = "Check your connection.";
      show("error");
      return;
    }
    ready(engine);
    const r = engine.triage(text);
    views.result.innerHTML = renderResult(text, r, engine.m.taxonomy);
    show("result");
    if (window.innerWidth < 900) views.result.scrollIntoView({ behavior: "smooth", block: "start" });
    requestAnimationFrame(() => {
      const arc = views.result.querySelector(".gauge__value");
      if (arc) requestAnimationFrame(() => (arc.style.strokeDashoffset = arc.dataset.target));
    });
    $("[data-copy-reply]", views.result).addEventListener("click", () => copy(formatReply(r), "Reply copied"));
    $("[data-share]", views.result).addEventListener("click", () => {
      const url = `${location.origin}${location.pathname}#check=${b64urlEncode(text)}`;
      history.replaceState(null, "", url);
      copy(url, "Link copied");
    });
    state.publish(text, r);
  }
  state.runCheck = (text) => { run(text); document.getElementById("check").scrollIntoView({ behavior: "smooth" }); };

  form.addEventListener("submit", (e) => { e.preventDefault(); samples.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", "false")); run(); });
  msg.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); run(); } });
  $("[data-clear]", root).addEventListener("click", () => { msg.value = ""; show("empty"); msg.focus(); });
  $("[data-retry]", root).addEventListener("click", () => run());
  $("[data-random]", root).addEventListener("click", async () => {
    if (!examples.length) {
      try { examples = (await (await fetch(new URL("../data/eval.json", import.meta.url))).json()).examples; } catch { examples = SAMPLES; }
    }
    run(examples[Math.floor(Math.random() * examples.length)].text);
  });

  loadEngine().then(ready).catch(() => (status.textContent = "model failed to load"));

  // Shared link: #check=<base64url>
  const m = location.hash.match(/^#check=([\w-]+)/);
  if (m) {
    try { const text = b64urlDecode(m[1]); msg.value = text; run(text); } catch { /* ignore malformed links */ }
  }
}
