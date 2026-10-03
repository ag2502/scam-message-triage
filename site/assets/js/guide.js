// Field guide: the ten scam types as a horizontal rail of cards.
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

export function initGuide({ state, loadEngine }) {
  const rail = $("[data-guide]");
  if (!rail) return;

  const render = (tax) => {
    rail.innerHTML = GUIDE.map(([id, icon, tells, example], i) => `
      <article class="card">
        <span class="card__icon"><i class="ph ${icon}"></i></span>
        <h3>${esc(tax?.[id]?.label || id)}</h3>
        <p>${esc(tax?.[id]?.description || "")}</p>
        <ul>${tells.map((t) => `<li>${esc(t)}</li>`).join("")}</ul>
        <blockquote>${esc(example)}</blockquote>
        <button class="btn btn--ghost btn--sm" type="button" data-try="${i}"><i class="ph ph-magnifying-glass"></i>Test this example</button>
      </article>`).join("");
  };
  render(null);
  loadEngine().then((e) => render(e.m.taxonomy)).catch(() => {});

  rail.addEventListener("click", (e) => {
    const b = e.target.closest("[data-try]");
    if (b) state.runCheck?.(GUIDE[+b.dataset.try][3]);
  });
  const step = () => Math.min(rail.clientWidth * 0.8, 720);
  $("[data-guide-prev]").addEventListener("click", () => rail.scrollBy({ left: -step(), behavior: "smooth" }));
  $("[data-guide-next]").addEventListener("click", () => rail.scrollBy({ left: step(), behavior: "smooth" }));
}
