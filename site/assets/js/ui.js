// Shared helpers for the site.

export const $ = (sel, root = document) => root.querySelector(sel);
export const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];

export const reducedMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

export function esc(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

let toastTimer;
export function toast(msg) {
  const el = $("[data-toast]");
  el.textContent = msg;
  el.classList.add("is-on");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("is-on"), 2200);
}

export async function copy(text, done = "Copied") {
  try {
    await navigator.clipboard.writeText(text);
    toast(done);
  } catch {
    toast("Couldn't copy. Select the text and copy it manually.");
  }
}

export const LEVEL_ICON = { high: "ph-fill ph-seal-warning", medium: "ph-fill ph-warning", low: "ph-fill ph-check-circle" };
export const LEVEL_LABEL = { high: "High risk", medium: "Medium risk", low: "Low risk" };
const BADGE = { high: "🔴 HIGH RISK", medium: "🟠 MEDIUM RISK", low: "🟢 LOW RISK" };

/** JS twin of scam_triage/reply.py format_reply(): the text the WhatsApp bot sends. */
/** Whole-number percent with round-half-even, like Python's f"{x:.0%}". */
export function pct0(x) {
  const v = x * 100, f = Math.floor(v);
  return Math.abs(v - f - 0.5) < 1e-9 ? (f % 2 === 0 ? f : f + 1) : Math.round(v);
}

export function formatReply(r) {
  const lines = [`${BADGE[r.risk_level]} (${pct0(r.risk_score)}%)`, ""];
  if (r.risk_level === "low") lines.push(`*${r.scam_type_label}.* ${r.summary}`);
  else {
    lines.push(`*Likely scam type:* ${r.scam_type_label}`);
    const i = r.summary.indexOf(". ");
    lines.push(i >= 0 ? r.summary.slice(i + 2) : r.summary);
  }
  if (r.from_context) lines.push(`_Based on the last ${r.thread_size} messages together._`);
  if (r.reasons.length) lines.push("", "*Why:*", ...r.reasons.map((x) => `• ${x}`));
  if (r.cautions?.length) lines.push("", "*Before you act:*", ...r.cautions.map((x) => `• ${x}`));
  if (r.next_steps.length) lines.push("", "*What to do:*", ...r.next_steps.map((x) => `• ${x}`));
  lines.push("", "_Automated check. It can be wrong. When in doubt, verify through a channel you already trust._");
  return lines.join("\n");
}

/** Render WhatsApp-style *bold* and _italic_ as HTML (input is escaped first). */
export function waMarkup(text) {
  return esc(text).replace(/\*([^*\n]+)\*/g, "<b>$1</b>").replace(/_([^_\n]+)_/g, "<i>$1</i>");
}

export function b64urlEncode(str) {
  const bytes = new TextEncoder().encode(str);
  let bin = "";
  bytes.forEach((b) => (bin += String.fromCharCode(b)));
  return btoa(bin).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

export function b64urlDecode(s) {
  const bin = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
  return new TextDecoder().decode(Uint8Array.from(bin, (c) => c.charCodeAt(0)));
}

/** Run `fn` once when `el` first scrolls near the viewport. */
export function whenNear(el, fn, rootMargin = "200px") {
  const io = new IntersectionObserver((entries) => {
    if (entries.some((e) => e.isIntersecting)) { io.disconnect(); fn(); }
  }, { rootMargin });
  io.observe(el);
}

export const pct = (v, d = 0) => `${(v * 100).toFixed(d)}%`;
