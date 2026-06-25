// MasterProps Service Worker v1 (25-jun-2026)
const CACHE = 'mp-v1';
const STATIC = ['/', '/manifest.json', '/icon-192.png', '/icon-512.png', '/og-image.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)).catch(()=>{}));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k !== CACHE).map(k => caches.delete(k))
  )));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // Solo cachear mismo origen, no JSONs dinámicos
  if (url.origin !== location.origin) return;
  if (url.pathname.endsWith('.json')) return; // siempre red para datos
  // Network-first para HTML
  if (req.mode === 'navigate' || req.headers.get('accept')?.includes('text/html')) {
    e.respondWith(
      fetch(req).then(res => {
        const cl = res.clone();
        caches.open(CACHE).then(c => c.put(req, cl));
        return res;
      }).catch(() => caches.match(req).then(r => r || caches.match('/')))
    );
    return;
  }
  // Cache-first para assets
  e.respondWith(
    caches.match(req).then(r => r || fetch(req).then(res => {
      const cl = res.clone();
      caches.open(CACHE).then(c => c.put(req, cl));
      return res;
    }))
  );
});

// Push handler (preparado para ETAPA 3)
self.addEventListener('push', e => {
  const data = e.data ? e.data.json() : {};
  const title = data.title || '💰 MasterProps';
  const opts = {
    body: data.body || 'Tu billete del día ya está listo',
    icon: '/icon-192.png',
    badge: '/icon-192.png',
    data: { url: data.url || '/' },
  };
  e.waitUntil(self.registration.showNotification(title, opts));
});
self.addEventListener('notificationclick', e => {
  e.notification.close();
  e.waitUntil(clients.openWindow(e.notification.data.url || '/'));
});
