// Scam types: a pinned horizontal pan on desktop, a swipeable rail on phones.
import { $, esc } from "./ui.js";

// Labels, descriptions and next steps come from the model's taxonomy; tells and examples are curated here.
const GUIDE = [
  ["family_impersonation", "ph-user-switch", ["A 'new number' or borrowed phone", "Can't call, text only", "Urgent and secret"],
    "Hey Dad, it's me, I lost my phone so text me here. I need $400 for a deposit by tonight, can you Zelle it? Please don't tell Mom"],
  ["fake_payment_receipt", "ph-receipt", ["Money 'sent by mistake'", "A screenshot instead of real money", "Asks you to send it back fast"],
    "Sorry, I sent R$700 to your Pix by mistake while paying my landlord. Can you return it to my key? Receipt attached"],
  ["bank_impersonation", "ph-bank", ["'Fraud team' asks you to act", "A 'safe account' or remote-access app", "Call this number now"],
    "HSBC Security: suspicious login detected. Your savings are at risk, transfer them to the protected account our agent gives you"],
  ["delivery_fee", "ph-package", ["Small fee to release a parcel", "Link to a look-alike courier site", "Deadline in hours"],
    "USPS: your package is held at our warehouse. Pay the $1.30 redelivery fee within 12 hours: usps-redeliver.top"],
  ["toll_fine_tax", "ph-car", ["Unpaid toll, fine or tax refund", "Threat of late fees or arrest", "Pay through a link"],
    "SunPass: You have an outstanding toll of $4.75. Avoid a $40 penalty by paying today at sunpass-billing.vip"],
  ["account_phishing", "ph-lock-key", ["Account locked or suspended", "'Verify' or 'update billing' link", "24-hour deadline"],
    "Netflix: we couldn't process your payment and your account is on hold. Update your card here: netflix-billing-help.com"],
  ["verification_code_theft", "ph-password", ["A code 'sent to you by mistake'", "Asks you to forward or read it", "Often from a 'friend' or 'group admin'"],
    "Hi, it's the admin of the parents' group, we're verifying members. You'll get a 6-digit code, please send it here"],
  ["prize_lottery", "ph-gift", ["You won something you never entered", "Pay a small fee to claim it", "Expires today"],
    "Congratulations! Your number won a $1,000 Walmart gift card. Pay $2.99 shipping to claim it: wmt-rewards.shop"],
  ["job_task", "ph-briefcase", ["Easy money for likes or reviews", "Small payouts at first", "Then 'recharge' to withdraw"],
    "Remote job! Rate hotels online and earn $300 a day. To unlock your commission, top up $150 to your task account"],
  ["investment_crypto", "ph-chart-line-up", ["Guaranteed or huge returns", "A 'mentor' or trading group", "Crypto deposits only"],
    "Join our VIP trading group: 40% weekly profit guaranteed. Minimum deposit 200 USDT, withdraw anytime"],
];

export function initTypes({ state, loadEngine }) {
  const root = $("[data-types]");
  if (!root) return;
  const track = $("[data-types-track]", root);
  const pin = $("[data-types-pin]", root);

  const render = (tax) => {
    track.querySelectorAll(".tpanel").forEach((n) => n.remove());
    track.insertAdjacentHTML("beforeend", GUIDE.map(([id, icon, tells, example], i) => `
      <article class="tpanel ${i % 3 === 1 ? "tpanel--tint" : i % 3 === 2 ? "tpanel--deep" : ""}">
        <i class="ph ${icon} tpanel__bg" aria-hidden="true"></i>
        <span class="card__icon"><i class="ph ${icon}"></i></span>
        <h3>${esc(tax?.[id]?.label || id)}</h3>
        <p>${esc(tax?.[id]?.description || "")}</p>
        <ul class="tpanel__tells">${tells.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
        <div class="tpanel__msg"><span class="wa-fwd"><i class="ph ph-share-fat"></i>Example</span>${esc(example)}</div>
        <button class="btn btn--ghost btn--sm" type="button" data-send="${i}"><i class="ph ph-paper-plane-right"></i>Send to the chat</button>
      </article>`).join(""));
  };
  render(null);
  track.addEventListener("click", (e) => {
    const b = e.target.closest("[data-send]");
    if (b) state.chatSend?.(GUIDE[+b.dataset.send][3]);
  });

  loadEngine().then((e) => {
    render(e.m.taxonomy);
    const gsap = window.gsap;
    if (!gsap || !window.ScrollTrigger) return;
    gsap.registerPlugin(window.ScrollTrigger);
    // Canonical horizontal pan: pin at "top top", scroll distance = horizontal travel.
    gsap.matchMedia().add("(min-width: 900px) and (prefers-reduced-motion: no-preference)", () => {
      root.classList.add("is-pinned");
      const distance = () => track.scrollWidth - window.innerWidth;
      const tween = gsap.to(track, {
        x: () => -distance(), ease: "none",
        scrollTrigger: { trigger: pin, start: "top top", end: () => `+=${distance()}`, pin: true, scrub: 1, invalidateOnRefresh: true },
      });
      return () => { root.classList.remove("is-pinned"); tween.scrollTrigger?.kill(); tween.kill(); };
    });
    window.ScrollTrigger.refresh();
  }).catch(() => {});
}
