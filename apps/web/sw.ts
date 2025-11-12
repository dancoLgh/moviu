/// <reference lib="webworker" />

const CACHE_NAME = 'moviu-precache-v1';
const OFFLINE_ROUTES = ['/portal', '/calendar', '/plans'];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(['/', '/manifest.json', ...OFFLINE_ROUTES]);
    })
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key)))
    )
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  if (request.method !== 'GET') return;
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      });
    })
  );
});

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? { title: 'moviu', body: 'Actualización en tu agenda.' };
  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      data,
      icon: '/icon-192.png'
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  event.waitUntil(self.clients.openWindow(event.notification.data?.url ?? '/portal'));
});

self.addEventListener('sync', (event) => {
  if (event.tag === 'moviu-sync-bookings') {
    event.waitUntil(Promise.resolve());
  }
});
