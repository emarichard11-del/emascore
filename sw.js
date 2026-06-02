const CACHE_NAME = 'emascore-v1';
const urlsToCache = [
  '/home.html',
  '/index.html',
  '/match.html',
  '/matches.html',
  '/league.html',
  '/favorites.html',
  '/account.html',
  '/settings.html',
  '/notifications.html',
  '/login.html',
  '/register.html',
  '/translations.js'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      if (response) return response;
      return fetch(event.request);
    })
  );
});
