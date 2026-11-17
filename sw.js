const STATIC = "static-v1", FILES = ["./", "index.html", "assets/css/style.css", "assets/js/app.js", "icon.svg"];
self.addEventListener("install", (e) => e.waitUntil(caches.open(STATIC).then((c) => c.addAll(FILES)).then(() => self.skipWaiting())));
self.addEventListener("activate", (e) => e.waitUntil(clients.claim()));
self.addEventListener("fetch", (e) => {
  const u = new URL(e.request.url);
  if (u.origin !== location.origin || e.request.method !== "GET") return;
  if (u.pathname.includes("/data/")) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
  } else {
    e.respondWith(caches.match(e.request).then((hit) => {
      const net = fetch(e.request).then((r) => { caches.open(STATIC).then((c) => c.put(e.request, r.clone())); return r; });
      return hit || net;
    }));
  }
});
