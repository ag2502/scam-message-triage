// "Get it" section: live API example and the in-app "check before you pay" sheet.
import { $, $$, esc, copy, toast, formatReply, LEVEL_ICON, whenNear } from "./ui.js";

const API_TEXT = "Hi, I sent you R$500 by Pix by mistake, can you send it back?";

const highlight = {
  json: (s) => esc(s)
    .replace(/(&quot;[^&]*?&quot;)(\s*:)/g, '<span class="k">$1</span>$2')
    .replace(/(:\s*)(&quot;.*?&quot;)/g, '$1<span class="s">$2</span>')
    .replace(/(:\s*)(-?\d+\.?\d*)/g, '$1<span class="n">$2</span>'),
  code: (s) => esc(s)
    .replace(/(#[^\n]*|\/\/[^\n]*)/g, '<span class="c">$1</span>')
    .replace(/(&quot;[^\n]*?&quot;|'[^'\n]*')/g, '<span class="s">$1</span>')
    .replace(/\b(import|from|const|await|print|curl|async|fetch|method|headers|body)\b/g, '<span class="k">$1</span>'),
};

function snippets(response) {
  return {
    curl: `curl -X POST https://your-host/v1/triage \\
  -H "Content-Type: application/json" \\
  -d '{"text": "${API_TEXT}"}'`,
    python: `import httpx

r = httpx.post("https://your-host/v1/triage",
               json={"text": "${API_TEXT}"})
verdict = r.json()
print(verdict["risk_level"], verdict["scam_type"])
print(verdict["reply_text"])  # ready to show the user`,
    js: `const res = await fetch("https://your-host/v1/triage", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ text: "${API_TEXT}" }),
});
const verdict = await res.json();
// verdict.risk_level, verdict.reasons, verdict.next_steps`,
    response,
  };
}

export function initChannels({ loadEngine }) {
  const code = $("[data-code]");
  const body = $("[data-code-body]");
  let current = "curl";
  let texts = snippets("// computing a real response...");

  const paint = () => {
    body.innerHTML = current === "response" ? highlight.json(texts.response) : highlight.code(texts[current]);
    $$("[data-tab]", code).forEach((b) => b.setAttribute("aria-selected", String(b.dataset.tab === current)));
  };
  $$("[data-tab]", code).forEach((b) => b.addEventListener("click", () => { current = b.dataset.tab; paint(); }));
  code.querySelector("[role=tablist]").addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    const tabs = $$("[data-tab]", code);
    const i = tabs.findIndex((t) => t.dataset.tab === current);
    const next = tabs[(i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
    current = next.dataset.tab; paint(); next.focus();
  });
  $("[data-copy-code]").addEventListener("click", () => copy(texts[current], "Code copied"));
  paint();

  // Bank payment sheet
  const sheet = $("[data-paysheet]");
  const payMsg = $("[data-pay-msg]");
  const verdictEl = $("[data-pay-verdict]");
  const payBtn = $("[data-pay-btn]");
  let lastLevel = "low";

  // The code block and bank sheet live inside toolbox windows (possibly hidden), so watch the section.
  whenNear(document.getElementById("toolbox") || code, async () => {
    let engine;
    try { engine = await loadEngine(); } catch { return; }
    const r = engine.triage(API_TEXT);
    const { extras, ...result } = r;
    texts = snippets(JSON.stringify({ ...result, reply_text: formatReply(r) }, null, 2));
    paint();

    let t;
    const check = () => {
      const text = payMsg.value.trim();
      if (!text) { verdictEl.innerHTML = ""; verdictEl.className = "paysheet__verdict"; payBtn.textContent = "Confirm payment"; return; }
      const v = engine.triage(text);
      lastLevel = v.risk_level;
      verdictEl.className = `paysheet__verdict lvl-${v.risk_level}`;
      verdictEl.innerHTML = v.risk_level === "low"
        ? `<strong><i class="${LEVEL_ICON.low}"></i>No scam patterns found</strong><p>Still, only pay people you've confirmed by phone.</p>`
        : `<strong><i class="${LEVEL_ICON[v.risk_level]}"></i>Stop. This looks like: ${esc(v.scam_type_label.toLowerCase())}</strong><p>${esc(v.next_steps[0])}</p>`;
      payBtn.textContent = v.risk_level === "low" ? "Confirm payment" : "Pay anyway";
      payBtn.classList.toggle("btn--ghost", v.risk_level !== "low");
      payBtn.classList.toggle("btn--primary", v.risk_level === "low");
    };
    payMsg.addEventListener("input", () => { clearTimeout(t); t = setTimeout(check, 180); });
    check();
  });
  payBtn.addEventListener("click", () => toast(lastLevel === "low" ? "Demo only: no money moves." : "Demo only. In a real app, this would ask you to call the person first."));
  void sheet;
}
