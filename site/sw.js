// Service worker: offline app shell + model. Pages are network-first (so deploys show up),
// assets are stale-while-revalidate. Videos are never cached (large, range requests).
const VERSION = "st-v1";
const PRECACHE = [
  "/", "/manifest.webmanifest",
  "/assets/css/style.css",
  "/assets/js/app.js", "/assets/js/engine.js", "/assets/js/ui.js", "/assets/js/chat.js", "/assets/js/checker.js",
  "/assets/js/story.js", "/assets/js/types.js", "/assets/js/game.js", "/assets/js/os.js", "/assets/js/xray.js",
  "/assets/js/apps.js", "/assets/js/channels.js", "/assets/js/results.js", "/assets/js/video.js", "/assets/js/pwa.js",
  "/assets/model/en.json", "/assets/data/eval.json",
  "/assets/fonts/geist.woff2", "/assets/fonts/geist-mono.woff2",
  "/assets/vendor/phosphor/regular.css", "/assets/vendor/phosphor/fill.css",
  "/assets/vendor/phosphor/Phosphor.woff2", "/assets/vendor/phosphor/Phosphor-Fill.woff2",
  "/assets/vendor/gsap/gsap.min.js", "/assets/vendor/gsap/ScrollTrigger.min.js",
  "/assets/img/favicon.svg", "/assets/img/icon-192.png", "/assets/img/icon-512.png",
];

self.addEventListener("install", (e) => {
  e.waitUntil(caches.open(VERSION).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (e) => {
  const req = e.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== location.origin || url.pathname.startsWith("/assets/video/")) return;

  if (req.mode === "navigate") {
    // Network first; offline falls back to the cached shell (query strings like ?text= still work).
    e.respondWith(fetch(req).catch(() => caches.match("/", { ignoreSearch: true })));
    return;
  }
  e.respondWith(
    caches.open(VERSION).then(async (cache) => {
      const cached = await cache.match(req);
      const network = fetch(req).then((res) => {
        if (res.ok && res.type === "basic") cache.put(req, res.clone());
        return res;
      }).catch(() => cached);
      return cached || network;
    }),
  );
});
