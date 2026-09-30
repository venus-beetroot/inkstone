// Inkstone service worker: optional. Put this file next to index.html to make the app work offline.
// The app shell is refreshed from the network when online; fonts and stroke data are kept once fetched.
const CACHE = 'inkstone-v1';

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(c => c.addAll(['./', './index.html'])).catch(() => {}));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);

  // App shell: network first so updates arrive, cache as the fallback.
  if (url.origin === location.origin) {
    event.respondWith(
      fetch(req)
        .then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); return res; })
        .catch(() => caches.match(req).then(hit => hit || caches.match('./index.html')))
    );
    return;
  }

  // Stroke data and fonts: cache first, they never change.
  if (/(^|\.)cdn\.jsdelivr\.net$|^fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) {
    event.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok || res.type === 'opaque') { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
        return res;
      }))
    );
  }
});
