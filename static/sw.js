const CACHE_NAME = 'hangarlink-v2.1';
const ASSETS_TO_CACHE = [
    '/',
    '/manifest.json',
    '/static/images/logo-192.png',
    '/static/images/logo-512.png',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap',
    'https://cdnjs.cloudflare.com/ajax/libs/flowbite/2.2.1/flowbite.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/flowbite/2.2.1/flowbite.min.js'
];

// Install Event
self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log('[Service Worker] Caching app shell assets');
            return cache.addAll(ASSETS_TO_CACHE);
        })
    );
    self.skipWaiting();
});

// Activate Event
self.addEventListener('activate', (event) => {
    event.waitUntil(
        caches.keys().then((cacheNames) => {
            return Promise.all(
                cacheNames.map((cache) => {
                    if (cache !== CACHE_NAME) {
                        console.log('[Service Worker] Deleting old cache:', cache);
                        return caches.delete(cache);
                    }
                })
            );
        })
    );
    return self.clients.claim();
});

// Fetch Event
self.addEventListener('fetch', (event) => {
    // Only handle GET requests
    if (event.request.method !== 'GET') return;

    // Skip Chrome extensions and other non-http(s) schemes
    if (!event.request.url.startsWith('http')) return;

    event.respondWith(
        caches.match(event.request).then((response) => {
            // Cache hit - return response
            if (response) {
                return response;
            }

            // Not in cache - fetch from network
            return fetch(event.request).then((fetchResponse) => {
                // If the response is valid, clone it and save it in cache (Optional: decide what to auto-cache)
                // For now, just return network result
                return fetchResponse;
            }).catch(() => {
                // If network fails and it's a navigation request, return index page (offline mode)
                if (event.request.mode === 'navigate') {
                    return caches.match('/');
                }
            });
        })
    );
});
