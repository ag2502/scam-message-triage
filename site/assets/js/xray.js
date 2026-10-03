// X-ray window: the five pipeline steps run on the last checked message (auto-advances until clicked).
import { $, $$, esc, formatReply, waMarkup } from "./ui.js";
import { signalName } from "./checker.js";

const DEFAULT_TEXT = "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now";
const TITLES = ["clean and mask", "warning signs", "features", "two models", "the reply"];

function maskHtml(pre) {
  return esc(pre).replace(/__(url|phone|amount)__/g, '<span class="tok mask">$1</span>').replace(/\b0\b/g, '<span class="tok mask">0</span>');
}

function render(step, text, r, engine) {
  const x = r.extras;
  switch (step) {
    case 0:
      return `<div class="row"><span class="k">Original</span><p class="pre">${esc(text)}</p></div>
        <div class="row"><span class="k">What the model reads</span><p class="pre">${maskHtml(x.preprocessed)}</p></div>`;
    case 1: {
      const fired = new Map(x.signals.map((s) => [s.id, s.evidence]));
      return `<div class="row"><span class="k">${fired.size} of ${engine.signalIds.length} signals fired</span>
        <div>${engine.signalIds.map((id) => `<span class="tok ${fired.has(id) ? "on" : ""}" title="${esc(fired.get(id) || "")}">${esc(signalName(id))}</span>`).join("")}</div></div>
        ${fired.size ? `<div class="row"><span class="k">Evidence</span><ul class="reasons">${[...fired].slice(0, 5).map(([id, ev]) => `<li><i class="ph ph-flag"></i><span><b>${esc(signalName(id))}</b>: "${esc(ev)}"</span></li>`).join("")}</ul></div>` : ""}`;
    }
    case 2: {
      const words = x.top_features.filter((f) => !f.name.startsWith("signal:")).slice(0, 7);
      const max = Math.max(...words.map((f) => Math.abs(f.contribution)), 0.001);
      return `<div class="row"><span class="k">${x.n_features} active features out of ${(engine.nWord + engine.nChar + engine.signalIds.length).toLocaleString()}</span>
        <ul class="bars">${words.map((f) => `<li><div><span class="name mono">${esc(f.name.startsWith("char:") ? `chars "${f.name.slice(5)}"` : `"${f.name}"`)}</span><span class="bar ${f.contribution < 0 ? "neg" : ""}" style="width:${Math.max(Math.abs(f.contribution) / max * 100, 2)}%"></span></div><span class="val">${f.contribution >= 0 ? "+" : ""}${f.contribution.toFixed(2)}</span></li>`).join("")}</ul></div>
        <p class="help">Bars show each feature's push toward "scam" (positive) or "legit" (negative).</p>`;
    }
    case 3: {
      const top = Object.entries(x.type_probs).sort((a, b) => b[1] - a[1]).slice(0, 3);
      const t = engine.m.thresholds;
      return `<div class="bigmath">risk logit = ${engine.m.risk.intercept.toFixed(2)} (bias) + ${(x.logit - engine.m.risk.intercept).toFixed(2)} (features)<br>
          = <b>${x.logit.toFixed(2)}</b> → sigmoid → <b>${(r.risk_score * 100).toFixed(1)}%</b></div>
        <div class="row"><span class="k">Levels: medium ≥ ${(t.medium * 100).toFixed(0)}%, high ≥ ${(t.high * 100).toFixed(0)}%. This message: <b>${r.risk_level}</b></span></div>
        <div class="row"><span class="k">Type model (softmax over 10 scam types)</span>
          <ul class="bars">${top.map(([c, p]) => `<li><div><span class="name">${esc(engine.m.taxonomy[c].label)}</span><span class="bar" style="width:${Math.max(p * 100, 2)}%"></span></div><span class="val">${(p * 100).toFixed(0)}%</span></li>`).join("")}</ul></div>`;
    }
    default:
      return `<div class="bubble bubble--in" style="max-width:100%;animation:none">${waMarkup(formatReply(r)).replace(/\n/g, "<br>")}</div>`;
  }
}

export function initXray({ state, loadEngine }) {
  const root = $("[data-xray]");
  if (!root) return;
  const body = $("[data-xray-body]", root);
  const steps = $("[data-xray-steps]", root);
  const src = $("[data-xray-src]", root);
  const win = root.closest(".oswin");
  let active = 0, engine = null, text = DEFAULT_TEXT, result = null, timer = 0, userPicked = false;

  steps.innerHTML = TITLES.map((t, i) => `<button type="button" role="tab" class="chip" data-step-btn="${i}" aria-selected="${i === 0}" aria-pressed="${i === 0}">${i + 1}. ${esc(t)}</button>`).join("");
  const paint = () => {
    if (!engine) return;
    result = result || engine.triage(text);
    body.innerHTML = render(active, text, result, engine);
    $$("[data-step-btn]", steps).forEach((b, i) => { b.setAttribute("aria-selected", i === active); b.setAttribute("aria-pressed", i === active); });
    src.textContent = text === DEFAULT_TEXT ? "Showing an example. Check any message in the chat or Checker and it appears here." : "Showing the last message you checked.";
  };
  steps.addEventListener("click", (e) => {
    const b = e.target.closest("[data-step-btn]");
    if (!b) return;
    userPicked = true;
    active = +b.dataset.stepBtn;
    paint();
  });
  // Auto-advance through the steps while the window is visible, until the user picks one.
  const loop = () => {
    clearInterval(timer);
    timer = setInterval(() => {
      if (userPicked || win?.hidden || document.hidden) return;
      active = (active + 1) % TITLES.length;
      paint();
    }, 3800);
  };
  state.onResult((t, r) => { text = t; result = r; active = 0; paint(); });
  loadEngine().then((e) => { engine = e; paint(); loop(); }).catch(() => (body.innerHTML = '<p class="help">The model did not load. Refresh to try again.</p>'));
}
