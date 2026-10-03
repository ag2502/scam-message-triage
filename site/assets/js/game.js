// Spot-the-scam: swipe real hand-written messages, you vs the on-device model.
import { $, $$, esc, toast, copy, reducedMotion, whenNear } from "./ui.js";

const ROUND = 10;
const SECONDS = 15;
const SITE = "https://scam-message-triage.vercel.app/#game";
const KAO = { idle: "(ง •̀_•́)ง", right: "( •̀ᴗ•́ )و", wrong: "(╥﹏╥)", slow: "(・_・;)", win: "\\(★ω★)/", lose: "(｡•́︿•̀｡)", tie: "(•_•)>⌐■-■" };

function shuffle(a) {
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
  return a;
}

export function initGame({ loadEngine }) {
  const root = $("[data-game]");
  if (!root) return;
  const stack = $("[data-stack]", root);
  const controls = $("[data-controls]", root);
  const timerBar = $("[data-timer]", root);
  const kao = $("[data-game-kao]", root);
  const hud = { you: $("[data-hud-you]", root), model: $("[data-hud-model]", root), streak: $("[data-hud-streak]", root), best: $("[data-hud-best]", root) };
  let pool = null, engine = null;
  let deck = [], idx = 0, score = { you: 0, model: 0, streak: 0, bestStreak: 0 }, answered = false, misses = [];
  let timer = 0, deadline = 0;

  const best = () => { try { return JSON.parse(localStorage.getItem("st-best") || "null"); } catch { return null; } };
  const saveBest = (v) => { try { localStorage.setItem("st-best", JSON.stringify(v)); } catch {} };
  const paintHud = () => {
    hud.you.textContent = score.you; hud.model.textContent = score.model; hud.streak.textContent = score.streak;
    const b = best();
    hud.best.textContent = b ? `Your best: ${b.you}/${ROUND} (model ${b.model}/${ROUND}).` : "";
  };

  async function loadPool() {
    if (pool) return pool;
    const data = await (await fetch(new URL("../data/eval.json", import.meta.url))).json();
    pool = { scam: [], legit: [] };
    for (const [name, set] of Object.entries(data.sets)) {
      if (!set.t) continue;
      set.t.forEach((text, i) => pool[set.y[i] ? "scam" : "legit"].push({ text, scam: !!set.y[i], src: name }));
    }
    return pool;
  }

  function intro() {
    stopTimer();
    controls.hidden = true;
    kao.textContent = KAO.idle;
    stack.innerHTML = `<article class="gcard gcard--intro"><div class="gcard__inner"><div class="gcard__face">
        <span class="kao gcard__kao">${KAO.idle}</span>
        <h3>Ready?</h3>
        <p>${ROUND} messages: half are scams, half are real. The model plays the same cards.</p>
        <button class="btn btn--primary" type="button" data-start><i class="ph-fill ph-play"></i>Start</button>
      </div></div></article>`;
    paintHud();
  }

  async function start() {
    try {
      [engine] = await Promise.all([loadEngine(), loadPool()]);
    } catch { toast("Couldn't load the game data. Check your connection."); return; }
    const pick = (arr, n) => shuffle([...arr]).slice(0, n);
    deck = shuffle([...pick(pool.scam, ROUND / 2), ...pick(pool.legit, ROUND / 2)]).map((c) => {
      const r = engine.triage(c.text);
      return { ...c, r, modelSaysScam: r.risk_level !== "low" };
    });
    idx = 0; misses = [];
    score = { you: 0, model: 0, streak: 0, bestStreak: 0 };
    controls.hidden = false;
    paintHud();
    renderStack();
  }

  function cardHtml(c, i) {
    return `<article class="gcard" data-card="${i}" style="--i:${i - idx}">
      <div class="gcard__inner">
        <div class="gcard__face gcard__front">
          <div class="gcard__from"><span class="chat__avatar"><i class="ph-fill ph-user"></i></span><div><strong>New message</strong><small>${i + 1} of ${ROUND}</small></div></div>
          <div class="gcard__bubble">${esc(c.text)}</div>
          <span class="stamp stamp--scam">Scam</span><span class="stamp stamp--real">Real</span>
        </div>
        <div class="gcard__face gcard__back" data-back></div>
      </div>
    </article>`;
  }

  function renderStack() {
    const upcoming = deck.slice(idx, idx + 3).map((c, k) => cardHtml(c, idx + k)).reverse().join("");
    stack.innerHTML = upcoming;
    answered = false;
    const top = $(`[data-card="${idx}"]`, stack);
    if (top) { bindDrag(top); startTimer(); }
  }

  // ---------- timer ----------
  function startTimer() {
    stopTimer();
    deadline = performance.now() + SECONDS * 1000;
    const tick = () => {
      const left = Math.max(0, deadline - performance.now());
      timerBar.style.transform = `scaleX(${left / (SECONDS * 1000)})`;
      timerBar.classList.toggle("is-low", left < 4000);
      if (left <= 0) { decide(null); return; }
      timer = requestAnimationFrame(tick);
    };
    timer = requestAnimationFrame(tick);
  }
  function stopTimer() { cancelAnimationFrame(timer); timer = 0; }

  // ---------- drag ----------
  function bindDrag(card) {
    let x0 = 0, y0 = 0, dx = 0, dy = 0, dragging = false;
    card.addEventListener("pointerdown", (e) => {
      if (answered || e.button !== 0) return;
      dragging = true; x0 = e.clientX; y0 = e.clientY;
      card.setPointerCapture(e.pointerId);
      card.classList.add("is-dragging");
    });
    card.addEventListener("pointermove", (e) => {
      if (!dragging) return;
      dx = e.clientX - x0; dy = e.clientY - y0;
      card.style.transform = `translate(${dx}px, ${dy * 0.3}px) rotate(${dx / 18}deg)`;
      card.style.setProperty("--scam", Math.max(0, Math.min(1, dx / 110)));
      card.style.setProperty("--real", Math.max(0, Math.min(1, -dx / 110)));
    });
    const end = () => {
      if (!dragging) return;
      dragging = false;
      card.classList.remove("is-dragging");
      if (Math.abs(dx) > 110) decide(dx > 0 ? "scam" : "real");
      else { card.style.transform = ""; card.style.setProperty("--scam", 0); card.style.setProperty("--real", 0); }
      dx = dy = 0;
    };
    card.addEventListener("pointerup", end);
    card.addEventListener("pointercancel", end);
  }

  // ---------- decisions ----------
  function decide(pick) {
    if (answered || idx >= deck.length) return;
    answered = true;
    stopTimer();
    const c = deck[idx];
    const card = $(`[data-card="${idx}"]`, stack);
    const right = pick !== null && (pick === "scam") === c.scam;
    const modelRight = c.modelSaysScam === c.scam;
    score.you += right ? 1 : 0;
    score.model += modelRight ? 1 : 0;
    score.streak = right ? score.streak + 1 : 0;
    score.bestStreak = Math.max(score.bestStreak, score.streak);
    if (!right) misses.push({ ...c, pick });
    kao.textContent = pick === null ? KAO.slow : right ? KAO.right : KAO.wrong;
    paintHud();

    const r = c.r;
    const truth = c.scam ? `Scam${r.risk_level !== "low" ? `: ${esc(r.scam_type_label.toLowerCase())}` : ""}` : "A real message";
    $("[data-back]", card).innerHTML = `
      <span class="kao gcard__kao">${pick === null ? KAO.slow : right ? KAO.right : KAO.wrong}</span>
      <h3 class="${right ? "is-right" : "is-wrong"}">${pick === null ? "Too slow" : right ? "Correct" : "Not quite"}</h3>
      <p class="gcard__truth">${c.scam ? '<i class="ph-fill ph-seal-warning"></i>' : '<i class="ph-fill ph-check-circle"></i>'}${truth}</p>
      <p class="gcard__model">Model said <b>${c.modelSaysScam ? "scam" : "real"}</b> (${Math.round(r.risk_score * 100)}% risk) ${modelRight ? "✓" : "✗"}</p>
      ${r.reasons[0] && c.scam ? `<p class="gcard__why">${esc(r.reasons[0])}</p>` : ""}
      ${pick === null ? '<p class="gcard__why">Scammers rely on you rushing. In real life, take your time.</p>' : ""}
      <button class="btn btn--primary btn--sm" type="button" data-next>${idx + 1 < deck.length ? "Next card" : "See results"}<i class="ph ph-arrow-right"></i></button>`;
    card.style.transform = "";
    card.dataset.dir = pick === "real" ? "left" : "right";
    card.classList.add("is-flipped");
    setTimeout(() => $("[data-next]", card)?.focus({ preventScroll: true }), 350);
  }

  function next() {
    const card = $(`[data-card="${idx}"]`, stack);
    if (card) card.classList.add(card.dataset.dir === "left" ? "fly-left" : "fly-right");
    idx++;
    setTimeout(() => (idx < deck.length ? renderStack() : results()), reducedMotion() ? 0 : 320);
  }

  function results() {
    stopTimer();
    controls.hidden = true;
    timerBar.style.transform = "scaleX(0)";
    const verdict = score.you > score.model ? "win" : score.you < score.model ? "lose" : "tie";
    const title = { win: "You beat the model!", lose: "The model wins this round", tie: "A tie" }[verdict];
    kao.textContent = KAO[verdict];
    const b = best();
    if (!b || score.you > b.you) saveBest({ you: score.you, model: score.model });
    paintHud();
    stack.innerHTML = `<article class="gcard gcard--result"><div class="gcard__inner"><div class="gcard__face">
      <span class="kao gcard__kao">${KAO[verdict]}</span>
      <h3>${title}</h3>
      <p class="gcard__score"><b>${score.you}</b>/${ROUND} you · <b>${score.model}</b>/${ROUND} model · best streak ${score.bestStreak}</p>
      ${misses.length ? `<details class="gcard__misses"><summary>Your ${misses.length} miss${misses.length > 1 ? "es" : ""}</summary><ul>${misses.map((m) => `<li><b>${m.scam ? "Scam" : "Real"}</b> ${m.pick === null ? "(timed out)" : ""}: ${esc(m.text.length > 110 ? m.text.slice(0, 110) + "..." : m.text)}</li>`).join("")}</ul></details>` : "<p>Perfect round. Scammers would hate you.</p>"}
      <div class="gcard__actions">
        <button class="btn btn--primary btn--sm" type="button" data-start><i class="ph ph-arrows-clockwise"></i>Play again</button>
        <button class="btn btn--ghost btn--sm" type="button" data-share-score><i class="ph ph-share-network"></i>Share score</button>
      </div></div></div></article>`;
  }

  async function share() {
    const text = `I spotted ${score.you}/${ROUND} scams on Scam Triage (the model got ${score.model}/${ROUND}). Can you beat it?`;
    if (navigator.share) { try { await navigator.share({ title: "Spot the scam", text, url: SITE }); return; } catch { /* cancelled */ } }
    copy(`${text} ${SITE}`, "Score copied. Paste it anywhere.");
  }

  // ---------- wiring ----------
  root.addEventListener("click", (e) => {
    if (e.target.closest("[data-start]")) start();
    else if (e.target.closest("[data-next]")) next();
    else if (e.target.closest("[data-share-score]")) share();
    else { const p = e.target.closest("[data-pick]"); if (p) decide(p.dataset.pick); }
  });
  // Arrow keys work while the game is on screen.
  let onScreen = false;
  new IntersectionObserver(([e]) => (onScreen = e.isIntersecting), { threshold: 0.4 }).observe(root);
  document.addEventListener("keydown", (e) => {
    if (!onScreen || !deck.length || e.target.closest("input, textarea")) return;
    if (!answered && e.key === "ArrowRight") { e.preventDefault(); decide("scam"); }
    else if (!answered && e.key === "ArrowLeft") { e.preventDefault(); decide("real"); }
    else if (answered && e.key === "ArrowRight" && idx < deck.length) { e.preventDefault(); next(); }
  });

  intro();
  whenNear(root, () => { loadPool().catch(() => {}); }, "600px");
}
