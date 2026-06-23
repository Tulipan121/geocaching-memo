const CACHE_NAME = 'memory-hunt-v2';
const ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './icon.svg',
  './game.json',
  './css/style.css',
  './js/app.js'
];

// Pre-cache every photo referenced in game.json too, so the whole game —
// pictures included — works offline even before each one has been scanned.
// (If a photo 404s for some reason, addAll would fail the whole install,
// so each photo is fetched individually and failures are ignored.)
async function precachePhotos(cache) {
  try {
    const res = await fetch('./game.json', { cache: 'no-store' });
    const game = await res.json();
    const photos = (game.pairs || [])
      .map((p) => p.photo)
      .filter(Boolean);
    await Promise.all(
      photos.map((src) =>
        fetch(src).then((r) => cache.put(src, r)).catch(() => {})
      )
    );
  } catch (e) { /* offline on first install, or no photos yet — fine */ }
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      await cache.addAll(ASSETS);
      await precachePhotos(cache);
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Cache-first for everything in this app, so the whole game works
// with no internet connection once it's been opened a single time.
self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => cached);
    })
  );
});
