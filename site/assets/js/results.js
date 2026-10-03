// Threshold explorer: recall / false alarms / precision recomputed live from per-message scores.
import { $, esc, whenNear } from "./ui.js";

const SETS = [
  ["challenge_v3", "Blind set", "60 hand-written messages, never used for tuning"],
  ["test", "Held-out templates", "Unseen generated phrasings + real SMS"],
  ["challenge_v2", "Hand-written v2", "80 messages, inspected after v0.2"],
  ["challenge", "Hand-written v1", "90 messages, inspected after v0.1"],
];
const W = 800, H = 210, PAD = { l: 64, r: 20, t: 18, b: 40 };
const ROWS = { 1: 62, 0: 142 };
const x = (s) => PAD.l + s * (W - PAD.l - PAD.r);
const fmtPct = (v) => (v == null || Number.isNaN(v) ? "n/a" : `${(v * 100).toFixed(v > 0 && v < 0.1 ? 1 : 0)}%`);

// Deterministic jitter so dots don't jump when the threshold moves.
const jitter = (i) => (((Math.sin(i * 12.9898) * 43758.5453) % 1) + 1) % 1 - 0.5;

function stats(set, thr, prev) {
  let tp = 0, fp = 0, fn = 0, tn = 0;
  set.y.forEach((y, i) => {
    const flagged = set.s[i] >= thr;
    if (y) flagged ? tp++ : fn++; else flagged ? fp++ : tn++;
  });
  const tpr = tp / Math.max(tp + fn, 1), fpr = fp / Math.max(fp + tn, 1);
  const precPrev = tpr * prev + fpr * (1 - prev) ? (tpr * prev) / (tpr * prev + fpr * (1 - prev)) : null;
  return { tp, fp, fn, tn, tpr, fpr, precPrev };
}

export function initResults() {
  const root = $("[data-explorer]");
  if (!root) return;
  whenNear(root, async () => {
    let data;
    try { data = await (await fetch(new URL("../data/eval.json", import.meta.url))).json(); } catch {
      $("[data-stats]", root).innerHTML = '<p class="help">Evaluation data failed to load.</p>';
      return;
    }
    build(root, data);
  }, "400px");
}

function build(root, data) {
  const segs = $("[data-sets]", root);
  const thrIn = $("[data-thr]", root), thrOut = $("[data-thr-out]", root);
  const prevIn = $("[data-prev]", root), prevOut = $("[data-prev-out]", root);
  const statsEl = $("[data-stats]", root), strip = $("[data-strip]", root), caption = $("[data-strip-caption]", root);
  const T = data.thresholds;
  let setKey = "challenge_v3";
  let thr = T.high;

  segs.innerHTML = SETS.filter(([k]) => data.sets[k]).map(([k, label]) =>
    `<button type="button" class="chip" role="radio" aria-checked="${k === setKey}" aria-pressed="${k === setKey}" data-set="${k}">${esc(label)}</button>`).join("");
  segs.addEventListener("click", (e) => {
    const b = e.target.closest("[data-set]");
    if (!b) return;
    setKey = b.dataset.set;
    segs.querySelectorAll("[data-set]").forEach((c) => { const on = c === b; c.setAttribute("aria-checked", on); c.setAttribute("aria-pressed", on); });
    drawDots();
    update();
  });
  root.querySelectorAll("[data-preset]").forEach((b) => b.addEventListener("click", () => { thr = T[b.dataset.preset]; update(); }));
  thrIn.addEventListener("input", () => { thr = +thrIn.value; update(); });
  prevIn.addEventListener("input", update);

  // ----- chart skeleton -----
  strip.innerHTML = `
    <div class="legend-row" aria-hidden="true">
      <span><i style="background:var(--series-scam)"></i>Scam</span>
      <span><i style="background:var(--series-legit)"></i>Legitimate</span>
      <span><i style="background:var(--muted);opacity:.35"></i>Faded: handled correctly</span>
    </div>
    <div class="strip-wrap">
      <svg viewBox="0 0 ${W} ${H}" data-svg>
        <text class="row-label" x="0" y="${ROWS[1] + 4}">Scam</text>
        <text class="row-label" x="0" y="${ROWS[0] + 4}">Legit</text>
        <line class="axis" x1="${PAD.l}" x2="${W - PAD.r}" y1="${H - PAD.b}" y2="${H - PAD.b}"/>
        ${[0, 0.25, 0.5, 0.75, 1].map((t) => `<text x="${x(t)}" y="${H - PAD.b + 18}" text-anchor="middle">${t}</text>`).join("")}
        <text x="${(PAD.l + W - PAD.r) / 2}" y="${H - 4}" text-anchor="middle">risk score</text>
        ${["medium", "high"].map((k) => `<line class="mark" x1="${x(T[k])}" x2="${x(T[k])}" y1="${PAD.t + 4}" y2="${H - PAD.b}"/>
          <text x="${x(T[k]) + 4}" y="${PAD.t + 6}" font-size="11">${k}</text>`).join("")}
        <g data-dots></g>
        <line class="thr" data-thr-line y1="${PAD.t - 4}" y2="${H - PAD.b}"/>
        <text class="thr-label" data-thr-label y="${PAD.t - 8}" text-anchor="middle"></text>
        <rect class="hit" data-hit x="${PAD.l - 8}" y="0" width="${W - PAD.l - PAD.r + 16}" height="${H - PAD.b}"/>
      </svg>
      <div class="tip" data-tip hidden></div>
    </div>
    <details class="table-view"><summary>View as table</summary><table data-table></table></details>`;
  const svg = $("[data-svg]", strip), dotsG = $("[data-dots]", strip), tip = $("[data-tip]", strip);
  const line = $("[data-thr-line]", strip), lineLabel = $("[data-thr-label]", strip), hit = $("[data-hit]", strip);

  function drawDots() {
    const set = data.sets[setKey];
    const r = set.y.length > 400 ? 3.2 : 4.5;
    dotsG.innerHTML = set.s.map((s, i) => {
      const cy = ROWS[set.y[i]] + jitter(i) * (set.y.length > 400 ? 44 : 34);
      return `<circle class="dot ${set.y[i] ? "dot-s" : "dot-l"}" data-i="${i}" cx="${x(s).toFixed(1)}" cy="${cy.toFixed(1)}" r="${r}"/>`;
    }).join("");
  }

  // Drag the threshold directly on the chart.
  const svgX = (e) => { const p = svg.getBoundingClientRect(); return ((e.clientX - p.left) / p.width) * W; };
  let dragging = false;
  hit.addEventListener("pointerdown", (e) => { dragging = true; hit.setPointerCapture(e.pointerId); setFrom(e); });
  hit.addEventListener("pointermove", (e) => { if (dragging) setFrom(e); });
  hit.addEventListener("pointerup", () => (dragging = false));
  const setFrom = (e) => { thr = Math.min(1, Math.max(0, (svgX(e) - PAD.l) / (W - PAD.l - PAD.r))); update(); };
  // Dots sit under the drag layer; tooltips use hit-testing on the dot nearest the pointer.
  hit.addEventListener("pointermove", (e) => {
    if (dragging) { tip.hidden = true; return; }
    const el = document.elementsFromPoint(e.clientX, e.clientY).find((n) => n.classList?.contains("dot"));
    if (!el) { tip.hidden = true; return; }
    const set = data.sets[setKey], i = +el.dataset.i;
    const label = set.y[i] ? "Scam" : "Legit";
    const flagged = set.s[i] >= thr;
    const verdict = set.y[i] ? (flagged ? "caught" : "missed") : (flagged ? "false alarm" : "passed");
    tip.innerHTML = `<b>${label}, score ${set.s[i].toFixed(3)}</b> · ${verdict}${set.t ? `<br>${esc(set.t[i].length > 140 ? set.t[i].slice(0, 140) + "..." : set.t[i])}` : ""}`;
    const box = strip.querySelector(".strip-wrap").getBoundingClientRect(), d = el.getBoundingClientRect();
    tip.style.left = `${Math.min(Math.max(d.left + d.width / 2 - box.left, 150), box.width - 150)}px`;
    tip.style.top = `${d.top - box.top}px`;
    tip.hidden = false;
  });
  hit.addEventListener("pointerleave", () => (tip.hidden = true));

  function update() {
    const set = data.sets[setKey];
    const prev = +prevIn.value / 100;
    thrIn.value = thr;
    thrOut.textContent = thr.toFixed(3);
    prevOut.textContent = `${prevIn.value}%`;
    const st = stats(set, thr, prev);
    const nS = st.tp + st.fn, nL = st.fp + st.tn;
    const per1000 = { caught: Math.round(1000 * prev * st.tpr), missed: Math.round(1000 * prev * (1 - st.tpr)), fa: Math.round(1000 * (1 - prev) * st.fpr) };
    statsEl.innerHTML = `
      <div class="stat stat--scam"><span class="stat__num">${fmtPct(st.tpr)}</span><span class="stat__label">Scams caught</span><span class="stat__note">${st.tp} of ${nS} scams flagged</span></div>
      <div class="stat stat--fa"><span class="stat__num">${fmtPct(st.fpr)}</span><span class="stat__label">False alarms</span><span class="stat__note">${st.fp} of ${nL} real messages flagged</span></div>
      <div class="stat"><span class="stat__num">${fmtPct(st.precPrev)}</span><span class="stat__label">Flags that are real scams</span><span class="stat__note">if ${prevIn.value}% of forwarded messages are scams</span></div>
      <div class="stat"><span class="stat__num">${per1000.caught}<small style="font-size:.45em;color:var(--muted)"> / ${per1000.missed} / ${per1000.fa}</small></span><span class="stat__label">Per 1,000 forwards</span><span class="stat__note">scams caught / missed / false alarms</span></div>`;
    line.setAttribute("x1", x(thr)); line.setAttribute("x2", x(thr));
    lineLabel.setAttribute("x", Math.min(Math.max(x(thr), PAD.l + 20), W - 30));
    lineLabel.textContent = thr.toFixed(2);
    dotsG.querySelectorAll(".dot").forEach((d) => {
      const i = +d.dataset.i;
      const correct = set.y[i] ? set.s[i] >= thr : set.s[i] < thr;
      d.classList.toggle("ok", correct);
    });
    const meta = SETS.find(([k]) => k === setKey);
    caption.textContent = `${meta[1]}: ${meta[2]}. Drag on the chart or use the slider to move the threshold. Bright dots are the mistakes.`;
    $("[data-table]", strip).innerHTML = `<thead><tr><th>At threshold ${thr.toFixed(3)}</th><th>Flagged</th><th>Not flagged</th></tr></thead>
      <tbody><tr><td>Scam (${nS})</td><td>${st.tp}</td><td>${st.fn}</td></tr><tr><td>Legit (${nL})</td><td>${st.fp}</td><td>${st.tn}</td></tr></tbody>`;
  }

  drawDots();
  update();
}
