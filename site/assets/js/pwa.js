// Installable app: service worker, install button, and text shared into the app
// (Android share sheet via the manifest's share_target, or the iOS Shortcut's ?text=).
import { $$, toast } from "./ui.js";

const isIOS = () => /iphone|ipad|ipod/i.test(navigator.userAgent) || (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
const isStandalone = () => window.matchMedia("(display-mode: standalone)").matches || navigator.standalone === true;

/** Text handed to the page by a share or a Shortcut: ?text=, ?title=, ?url= (any subset). */
export function sharedText(search = location.search) {
  const q = new URLSearchParams(search);
  const parts = ["title", "text", "url"].map((k) => (q.get(k) || "").trim()).filter(Boolean);
  // Some apps repeat the same content in several fields.
  return [...new Set(parts)].join("\n").slice(0, 4000);
}

export function initPWA({ state }) {
  if ("serviceWorker" in navigator && window.isSecureContext) {
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }

  // Install button (Chrome/Edge/Android); iPhone gets "Add to Home Screen" instructions instead.
  let deferred = null;
  const buttons = $$("[data-install]");
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    deferred = e;
    buttons.forEach((b) => (b.hidden = false));
  });
  buttons.forEach((b) => b.addEventListener("click", async () => {
    if (!deferred) return;
    deferred.prompt();
    const { outcome } = await deferred.userChoice;
    deferred = null;
    buttons.forEach((x) => (x.hidden = true));
    if (outcome === "accepted") toast("Installed. Share any message to Scam Triage to check it.");
  }));
  window.addEventListener("appinstalled", () => buttons.forEach((b) => (b.hidden = true)));
  if (isIOS() && !isStandalone()) $$("[data-ios-install]").forEach((p) => (p.hidden = false));

  // Incoming shared text -> straight into the chat.
  const text = sharedText();
  if (text) {
    history.replaceState(null, "", location.pathname + location.hash); // drop ?text= from the address bar
    state.chatSend?.(text);
  }
}
