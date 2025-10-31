// Service Worker for KvízAréna PWA
// Placeholder for future offline functionality

self.addEventListener('install', (event) => {
    console.log('Service Worker installed');
});

self.addEventListener('activate', (event) => {
    console.log('Service Worker activated');
});

self.addEventListener('fetch', (event) => {
    // For now, just pass through all requests
    event.respondWith(fetch(event.request));
});
