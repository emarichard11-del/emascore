const CACHE_NAME = 'emascore-v4';
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
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(urlsToCache);
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(keys.filter(function(key) {
        return key !== CACHE_NAME;
      }).map(function(key) {
        return caches.delete(key);
      }));
    }).then(function() {
      return self.clients.claim();
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    fetch(event.request).catch(function() {
      return caches.match(event.request);
    })
  );
});
