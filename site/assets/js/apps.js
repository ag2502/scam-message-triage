// Toolbox apps: API console (simulated POST /v1/triage) and a terminal that emulates the scam-triage CLI.
import { $, esc, formatReply } from "./ui.js";
import { SAMPLES } from "./checker.js";

const highlightJson = (s) => esc(s)
  .replace(/(&quot;[^&]*?&quot;)(\s*:)/g, '<span class="k">$1</span>$2')
  .replace(/(:\s*)(&quot;.*?&quot;)/g, '$1<span class="s">$2</span>')
  .replace(/(:\s*)(-?\d+\.?\d*)/g, '$1<span class="n">$2</span>');

function apiResponse(engine, text) {
  const r = engine.triage(text);
  const { extras, ...result } = r;
  return { r, json: { ...result, reply_text: formatReply(r) } };
}

export function initApi({ loadEngine }) {
  const root = $("[data-api]");
  if (!root) return;
  const form = $("[data-api-form]", root);
  const bodyIn = $("[data-api-body]", root);
  const status = $("[data-api-status]", root);
  const out = $("[data-api-out]", root);
  bodyIn.value = JSON.stringify({ text: "Hi, I sent you R$500 by Pix by mistake, can you send it back?", lang: "en" }, null, 2);

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    status.className = "apicon__status";
    status.textContent = "Sending...";
    let req;
    try { req = JSON.parse(bodyIn.value); } catch (err) {
      return fail(400, { detail: `Invalid JSON: ${err.message}` });
    }
    if (typeof req.text !== "string" || !req.text.trim()) return fail(422, { detail: [{ loc: ["body", "text"], msg: "Field required (non-empty string)" }] });
    if (req.text.length > 4000) return fail(422, { detail: [{ loc: ["body", "text"], msg: "String should have at most 4000 characters" }] });
    if (req.lang && req.lang !== "en") return fail(422, { detail: [{ loc: ["body", "lang"], msg: "Input should be 'en'" }] });
    let engine;
    try { engine = await loadEngine(); } catch { return fail(503, { detail: "Model not loaded" }); }
    const t0 = performance.now();
    const { json } = apiResponse(engine, req.text);
    const ms = performance.now() - t0;
    status.innerHTML = `<b class="ok">200 OK</b> · ${ms.toFixed(1)} ms · application/json`;
    out.innerHTML = highlightJson(JSON.stringify(json, null, 2));
  });
  function fail(code, payload) {
    status.innerHTML = `<b class="bad">${code} ${code === 400 ? "Bad Request" : code === 422 ? "Unprocessable Entity" : "Service Unavailable"}</b> · application/json`;
    out.innerHTML = highlightJson(JSON.stringify(payload, null, 2));
  }
  bodyIn.addEventListener("keydown", (e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) form.requestSubmit(); });
}

const HELP = `Commands:
  scam-triage "message"          check a message (same output as the real CLI)
  scam-triage --json "message"   full JSON result
  samples                        list example messages
  sample <n>                     check example n
  clear                          clear the screen
  about                          what this is`;

export function initTerminal({ loadEngine }) {
  const root = $("[data-term]");
  if (!root) return;
  const out = $("[data-term-out]", root);
  const form = $("[data-term-form]", root);
  const input = $("[data-term-in]", root);
  const history = [];
  let hi = 0;

  const print = (text, cls = "") => {
    const el = document.createElement("pre");
    el.className = `term__l ${cls}`;
    el.textContent = text;
    out.append(el);
    root.scrollTop = root.scrollHeight;
  };
  const colorize = (el, level) => el.classList.add(`term__${level}`);

  async function run(cmd) {
    print(`~ % ${cmd}`, "term__cmd");
    const line = cmd.trim();
    if (!line) return;
    if (line === "clear") { out.innerHTML = ""; return; }
    if (line === "help") return print(HELP);
    if (line === "about") return print("Scam Triage: an explainable scam checker. This terminal runs the real model in your browser.\nSource: github.com/ag2502/scam-message-triage");
    if (line === "samples") return print(SAMPLES.map((s, i) => `  ${i + 1}. ${s.label}`).join("\n") + "\nRun: sample <n>");
    let m = line.match(/^sample\s+(\d+)$/);
    if (m) {
      const s = SAMPLES[+m[1] - 1];
      if (!s) return print(`sample: no example ${m[1]} (try 1-${SAMPLES.length})`, "term__err");
      return run(`scam-triage "${s.text.replace(/"/g, '\\"')}"`);
    }
    m = line.match(/^scam-triage(\s+--json)?\s+(["'])([\s\S]*)\2$/);
    if (m) {
      let engine;
      try { engine = await loadEngine(); } catch { return print("error: model failed to load", "term__err"); }
      const text = m[3].replace(/\\"/g, '"');
      if (!text.trim()) return print("scam-triage: error: no message given", "term__err");
      const r = engine.triage(text);
      if (m[1]) { const { extras, ...res } = r; return print(JSON.stringify(res, null, 2)); }
      const el = document.createElement("pre");
      el.className = "term__l";
      el.textContent = formatReply(r).replace(/\*/g, "").replace(/_/g, "");
      colorize(el, r.risk_level);
      out.append(el);
      root.scrollTop = root.scrollHeight;
      return;
    }
    if (/^scam-triage\b/.test(line)) return print('usage: scam-triage [--json] "message"   (wrap the message in quotes)', "term__err");
    print(`zsh: command not found: ${line.split(/\s+/)[0]}  (type "help")`, "term__err");
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const cmd = input.value;
    input.value = "";
    if (cmd.trim()) { history.push(cmd); hi = history.length; }
    run(cmd);
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowUp" && hi > 0) { e.preventDefault(); input.value = history[--hi]; }
    else if (e.key === "ArrowDown") { e.preventDefault(); hi = Math.min(history.length, hi + 1); input.value = history[hi] || ""; }
  });
  root.addEventListener("click", (e) => { if (!window.getSelection()?.toString() && !e.target.closest("a")) input.focus({ preventScroll: true }); });

  print('Scam Triage terminal. The model runs in this tab.\nType "help", or try:  sample 1');
}
