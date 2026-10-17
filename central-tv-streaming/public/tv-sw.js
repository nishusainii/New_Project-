// Central TV Streaming - Service Worker for Offline Video Caching
// Caches media files so the TV continues playing even if the server goes offline

const CACHE_NAME = 'central-tv-media-v4';
const MEDIA_CACHE_NAME = 'central-tv-video-v4';

// Assets to cache immediately on install
const STATIC_ASSETS = [
  '/player.html',
  '/js/player.js',
  '/js/hls.min.js',
  '/css/style.css',
  '/logo.png'
];

self.addEventListener('install', (event) => {
  console.log('[SW] Installing Central TV Service Worker...');
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      return cache.addAll(STATIC_ASSETS).catch(err => {
        console.warn('[SW] Failed to pre-cache some static assets:', err);
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Activated. Cleaning old caches...');
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k !== CACHE_NAME && k !== MEDIA_CACHE_NAME)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// Fetch strategy:
// - /media/* files: Cache-first with network fallback (video files, serve from cache if offline)
// - /api/* : Network-only (always fresh from server)
// - Everything else: Network-first with cache fallback
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests and WebSocket upgrades
  if (event.request.method !== 'GET') return;
  if (event.request.headers.get('upgrade') === 'websocket') return;

  // API calls: always go to network, never cache
  if (url.pathname.startsWith('/api/') ||
      url.pathname.startsWith('/webrtc/') ||
      url.pathname.startsWith('/hls/')) {
    return;
  }

  // Media files: Cache-first strategy
  // The 76MB seamless loop is cached once, then served locally forever
  if (url.pathname.startsWith('/media/')) {
    event.respondWith(
      caches.open(MEDIA_CACHE_NAME).then(async (cache) => {
        const cached = await cache.match(event.request);
        if (cached) {
          // Serve from cache immediately, try to revalidate in background
          console.log('[SW] Serving media from cache:', url.pathname);
          return cached;
        }

        // Not in cache: fetch from network and cache it
        try {
          console.log('[SW] Fetching and caching media:', url.pathname);
          const response = await fetch(event.request);
          if (response.ok && response.status === 200) {
            // Clone before consuming - cache the full file
            const responseToCache = response.clone();
            cache.put(event.request, responseToCache).catch(err => {
              console.warn('[SW] Failed to cache media (storage full?):', url.pathname, err.message);
            });
          }
          return response;
        } catch (err) {
          console.error('[SW] Network failed for media and no cache exists:', url.pathname);
          return new Response('Video file unavailable - server offline', {
            status: 503,
            statusText: 'Service Unavailable'
          });
        }
      })
    );
    return;
  }

  // Static assets: Network-first, cache fallback
  event.respondWith(
    fetch(event.request).then(response => {
      if (response.ok) {
        const responseToCache = response.clone();
        caches.open(CACHE_NAME).then(cache => cache.put(event.request, responseToCache));
      }
      return response;
    }).catch(() => {
      return caches.match(event.request).then(cached => {
        if (cached) return cached;
        return new Response('Offline', { status: 503 });
      });
    })
  );
});

// Listen for messages from player.js to pre-cache specific video files
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'PRECACHE_MEDIA') {
    const urls = event.data.urls || [];
    console.log('[SW] Pre-caching', urls.length, 'media file(s)...');
    caches.open(MEDIA_CACHE_NAME).then(async (cache) => {
      for (const url of urls) {
        const existing = await cache.match(url);
        if (!existing) {
          try {
            const response = await fetch(url);
            if (response.ok) {
              await cache.put(url, response);
              console.log('[SW] Pre-cached:', url);
            }
          } catch (err) {
            console.warn('[SW] Could not pre-cache:', url, err.message);
          }
        } else {
          console.log('[SW] Already cached:', url);
        }
      }
      // Notify all TV player tabs that pre-caching is complete
      const clients = await self.clients.matchAll();
      clients.forEach(client => client.postMessage({ type: 'PRECACHE_COMPLETE' }));
    });
  }

  if (event.data && event.data.type === 'CLEAR_MEDIA_CACHE') {
    caches.delete(MEDIA_CACHE_NAME).then(() => {
      console.log('[SW] Media cache cleared.');
    });
  }
});
