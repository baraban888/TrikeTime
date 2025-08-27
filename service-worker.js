const CACHE_NAME = "triketime-cache-v2";
const ASSETS = [
    "/",
    "/static/style.css",
    "/static/lang.js",
    "/static/manifest.json",
    "/static/icon-192.png",
    "/static/icon-512.png",
    "/static/icon-core.js",
    "/static/icon-al-helper.js",
];
self.addEventListener("install", event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache)));
});
self.addEventListener("fetch", event => {
    event.respondWith(caches.match(event.request).then(response => response || fetch(event.request)));
});
