// Usable WhatsApp-style chat with the bot. Everything runs on-device with the in-browser engine.
import { $, $$, esc, reducedMotion, LEVEL_LABEL, LEVEL_ICON } from "./ui.js";
import { markText } from "./checker.js";

const EMOJI = { high: "🔴", medium: "🟠", low: "🟢" };
const CHIPS = [
  ["👩‍👧", "Hi Mum scam", "Hi Mum, I dropped my phone so this is my new number. Can you send R$800 by Pix today? It's urgent and I can't talk right now"],
  ["📦", "Parcel fee", "Royal Mail: your parcel is on hold due to an unpaid £1.99 redelivery fee. Pay within 24 hours: royalmail-redelivery.top/pay"],
  ["🏦", "Fake bank", "Chase Fraud Alert: we blocked a payment of $1,940. To protect your savings, move your money to the safe account our agent gives you. Call +1 (415) 555 0182 now"],
  ["💸", "Pix by mistake", "Hi, I accidentally sent you R$450 by Pix, it was meant for my landlord. Could you please send it back to my key? I'm sending the receipt"],
  ["🔑", "Code by mistake", "Hey, sorry, I sent a 6-digit code to your number by mistake. Can you forward it to me?"],
  ["🚗", "Toll notice", "E-ZPass: you have an unpaid toll of $6.89. Pay now to avoid a $50 late fee: ezpass-tollpay.vip"],
  ["✅", "Real receipt", "Nubank: you sent a Pix of R$120.00 to Ana Souza."],
  ["✅", "Real OTP", "Your WhatsApp code: 482-019. Don't share this code with others."],
];
const EMOJIS = ["🙏", "😩", "😂", "❤️", "👍", "🚨", "💸", "📦", "🏦", "🔑", "😊", "🤔"];
const GREETINGS = /^(hi|hello|hey|oi|olá|ola|hola|help|start|menu)[!. ]*$/i;
const wait = (ms) => new Promise((r) => setTimeout(r, reducedMotion() ? Math.min(ms, 120) : ms));
const clock = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

export function initChat({ state, loadEngine }) {
  const root = $("[data-chat]");
  if (!root) return;
  const body = $("[data-chat-body]", root);
  const input = $("[data-chat-input]", root);
  const form = $("[data-chat-form]", root);
  const sendBtn = $("[data-chat-send]", root);
  const sendIcon = $("[data-chat-send-icon]", root);
  const status = $("[data-chat-status]", root);
  const jump = $("[data-chat-jump]", root);
  const emojiPanel = $("[data-chat-emoji]", root);
  const fileInput = $("[data-chat-file]", root);
  const rec = $("[data-chat-rec]", root);
  const recTime = $("[data-chat-rec-time]", root);
  const lastResults = new Map(); // message id -> {text, result}
  let seq = 0;
  let queue = Promise.resolve();

  setInterval(() => { const c = $("[data-clock]", root); if (c) c.textContent = new Date().toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }).replace(/\s?[AP]M/i, ""); }, 15000);

  // ---------- rendering ----------
  const nearBottom = () => body.scrollHeight - body.scrollTop - body.clientHeight < 80;
  const toBottom = (smooth = true) => body.scrollTo({ top: body.scrollHeight, behavior: smooth && !reducedMotion() ? "smooth" : "auto" });
  body.addEventListener("scroll", () => (jump.hidden = nearBottom()), { passive: true });
  jump.addEventListener("click", () => toBottom());

  function add(html, cls, { stick = true } = {}) {
    const stuck = nearBottom();
    const el = document.createElement("div");
    el.className = cls;
    el.innerHTML = html;
    body.append(el);
    if (stick || stuck) requestAnimationFrame(() => toBottom());
    return el;
  }
  const system = (html) => add(html, "wa-sys");
  const botBubble = (html, buttons = []) => {
    const id = ++seq;
    const el = add(`<div class="wa-b wa-b--in">${html}<span class="wa-meta">${clock()}</span></div>${
      buttons.length ? `<div class="wa-btns">${buttons.map(([act, label, icon]) => `<button type="button" data-act="${act}" data-ref="${id}"><i class="ph ${icon}"></i>${esc(label)}</button>`).join("")}</div>` : ""}`, "wa-row wa-row--in");
    return { el, id };
  };
  const userBubble = (html, { forwarded = false } = {}) => {
    const el = add(`<div class="wa-b wa-b--out">${forwarded ? '<span class="wa-fwd"><i class="ph ph-share-fat"></i>Forwarded</span>' : ""}${html}<span class="wa-meta">${clock()} <i class="ph ph-check" data-tick></i></span></div>`, "wa-row wa-row--out");
    const tick = $("[data-tick]", el);
    setTimeout(() => (tick.className = "ph ph-checks"), 350);
    return { el, read: () => tick.classList.add("is-read") };
  };
  const typing = () => add('<div class="typing"><i></i><i></i><i></i></div>', "wa-row wa-row--in");

  async function botSays(html, buttons, delay = 700) {
    status.textContent = "typing...";
    const t = typing();
    await wait(delay);
    t.remove();
    status.textContent = "online";
    return botBubble(html, buttons);
  }

  // ---------- bot logic ----------
  function verdictHtml(r) {
    const why = r.reasons.slice(0, 2).map((x) => `<li>${esc(x)}</li>`).join("");
    return `<div class="wa-verdict lvl-${r.risk_level}">
        <span class="badge"><i class="${LEVEL_ICON[r.risk_level]}"></i>${LEVEL_LABEL[r.risk_level]} ${EMOJI[r.risk_level]} ${Math.round(r.risk_score * 100)}%</span>
        <strong>${esc(r.scam_type_label)}</strong>
        ${r.risk_level === "low" ? `<p>${esc(r.summary)}</p>` : `${why ? `<ul>${why}</ul>` : ""}<p><b>Next:</b> ${esc(r.next_steps[0])}</p>`}
      </div>`;
  }

  async function handleText(text, forwarded) {
    const u = userBubble(esc(text).replace(/\n/g, "<br>"), { forwarded });
    const t = text.trim();
    if (GREETINGS.test(t)) { u.read(); return welcome(); }
    if (t.length < 12) {
      u.read();
      return botSays("That's a bit short to judge. <b>Paste the whole message</b> you received, or tap one of the examples below.", [], 600);
    }
    status.textContent = "typing...";
    const tp = typing();
    let engine;
    try { engine = await loadEngine(); } catch {
      tp.remove(); status.textContent = "offline";
      return botBubble("I couldn't load my model. Check your connection and try again.");
    }
    u.read();
    const r = engine.triage(t);
    await wait(Math.min(1500, 650 + t.length * 4));
    tp.remove();
    status.textContent = "online";
    const buttons = r.risk_level === "low"
      ? [["safe", "Why does it look OK?", "ph-question"], ["words", "Show me the words", "ph-highlighter-circle"]]
      : [["why", "Why?", "ph-question"], ["todo", "What should I do?", "ph-list-checks"], ["words", "Show me the words", "ph-highlighter-circle"]];
    const b = botBubble(verdictHtml(r), buttons);
    lastResults.set(String(b.id), { text: t, r });
    state.publish(t, r);
  }

  async function act(action, ref, label) {
    const ctx = lastResults.get(ref);
    if (!ctx) return;
    const { text, r } = ctx;
    userBubble(esc(label)).read();
    if (action === "why") {
      return botSays(`<b>Why I flagged it:</b><ul class="wa-list">${r.reasons.map((x) => `<li><i class="ph-fill ph-flag"></i>${esc(x)}</li>`).join("") || "<li>The wording as a whole matches scams I've seen.</li>"}</ul>`,
        [["sure", "Are you sure?", "ph-scales"]]);
    }
    if (action === "todo") {
      return botSays(`<b>What to do:</b><ol class="wa-list wa-list--num">${r.next_steps.map((x) => `<li>${esc(x)}</li>`).join("")}</ol>`);
    }
    if (action === "words") {
      return botSays(`<div class="lvl-${r.risk_level}"><b>The words that mattered:</b><p class="marked wa-marked">${markText(text, r)}</p><small class="wa-legend">solid: warning sign · dotted: phrase I weighed</small></div>`);
    }
    if (action === "safe") {
      return botSays(`I didn't find the usual pressure tactics: no new number, no urgent request to pay, no suspicious link or code request. ${r.reasons.length ? "A couple of things are still worth a second look." : ""}<br><br>If it asks you for money or a code later, check again.`);
    }
    if (action === "sure") {
      return botSays("No, and I won't pretend to be. On a blind test of 60 hand-written messages, my <b>high</b> level caught 26 of 30 scams with no false alarms, and <b>medium</b> caught 28 of 30 with 1 false alarm. When money is involved, call the person on a number you already have.");
    }
  }

  async function welcome() {
    return botSays("Hi! I'm the <b>Scam Triage</b> bot 👋<br>Paste or forward a message that's asking you for money, a code or a quick payment. I'll tell you how risky it looks and what to do.", [], 500);
  }

  // ---------- input ----------
  const enqueue = (fn) => (queue = queue.then(fn).catch((e) => console.error(e)));
  const refreshSend = () => {
    const hasText = input.value.trim().length > 0;
    sendIcon.className = hasText ? "ph-fill ph-paper-plane-right" : "ph-fill ph-microphone";
    sendBtn.setAttribute("aria-label", hasText ? "Send" : "Hold to record a voice note");
    input.style.height = "auto";
    input.style.height = `${Math.min(input.scrollHeight, 120)}px`;
  };
  input.addEventListener("input", refreshSend);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    refreshSend();
    emojiPanel.hidden = true;
    enqueue(() => handleText(text, false));
  });

  // Quick-reply buttons
  body.addEventListener("click", (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    b.parentElement.querySelectorAll("button").forEach((x) => (x.disabled = true));
    b.classList.add("is-picked");
    enqueue(() => act(b.dataset.act, b.dataset.ref, b.textContent.trim()));
  });

  // Example chips
  const chips = $("[data-chat-chips]", root);
  chips.innerHTML = CHIPS.map(([e, label], i) => `<button type="button" data-chip="${i}"><span aria-hidden="true">${e}</span>${esc(label)}</button>`).join("");
  chips.addEventListener("click", (e) => {
    const c = e.target.closest("[data-chip]");
    if (c) enqueue(() => handleText(CHIPS[+c.dataset.chip][2], true));
  });

  // Emoji picker
  emojiPanel.innerHTML = EMOJIS.map((x) => `<button type="button">${x}</button>`).join("");
  $("[data-chat-emoji-btn]", root).addEventListener("click", () => (emojiPanel.hidden = !emojiPanel.hidden));
  emojiPanel.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    const pos = input.selectionStart ?? input.value.length;
    input.value = input.value.slice(0, pos) + b.textContent + input.value.slice(pos);
    input.focus();
    refreshSend();
  });

  // Photo: shown locally only, never uploaded.
  $("[data-chat-attach]", root).addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", () => {
    const f = fileInput.files?.[0];
    if (!f) return;
    const url = URL.createObjectURL(f);
    fileInput.value = "";
    enqueue(async () => {
      userBubble(`<img class="wa-img" src="${url}" alt="Photo you attached (stays on your device)">`).read();
      await botSays("I can only read text for now. If that's a screenshot of a message, <b>paste its text</b> here and I'll check it. (Your photo stayed on your device.)", [], 800);
    });
  });

  // Voice note: hold the mic. Simulated; the microphone is never opened.
  let recStart = 0, recTimer = 0;
  const stopRec = (send) => {
    if (!recStart) return;
    clearInterval(recTimer);
    const secs = Math.max(1, Math.round((performance.now() - recStart) / 1000));
    recStart = 0;
    rec.hidden = true;
    root.classList.remove("is-recording");
    if (!send) return;
    const bars = Array.from({ length: 26 }, (_, i) => `<i style="height:${30 + Math.round(Math.abs(Math.sin(i * 1.7 + secs)) * 70)}%"></i>`).join("");
    enqueue(async () => {
      userBubble(`<span class="wa-voice"><i class="ph-fill ph-play"></i><span class="wa-wave">${bars}</span><small>0:${String(secs).padStart(2, "0")}</small></span>`).read();
      await botSays("I can't listen to voice notes yet. Scammers do send fake voice notes, though, sometimes cloned from a real relative's voice. <b>Call them back on the number you already have.</b>", [], 900);
    });
  };
  sendBtn.addEventListener("pointerdown", (e) => {
    if (input.value.trim()) return;
    e.preventDefault();
    recStart = performance.now();
    rec.hidden = false;
    root.classList.add("is-recording");
    recTimer = setInterval(() => { const s = Math.floor((performance.now() - recStart) / 1000); recTime.textContent = `0:${String(s).padStart(2, "0")}`; }, 250);
    recTime.textContent = "0:00";
  });
  sendBtn.addEventListener("pointerup", () => stopRec(true));
  sendBtn.addEventListener("pointerleave", () => stopRec(false));
  sendBtn.addEventListener("click", (e) => { if (!input.value.trim()) e.preventDefault(); });

  // Public: other sections can send a message here.
  state.chatSend = (text) => {
    document.getElementById("chat").scrollIntoView({ behavior: reducedMotion() ? "auto" : "smooth", block: "center" });
    enqueue(() => handleText(text, true));
  };

  // Opening
  system('<i class="ph ph-lock-simple"></i> This chat runs on your device. Nothing you send leaves this page.');
  enqueue(async () => { await wait(500); await welcome(); });
}
