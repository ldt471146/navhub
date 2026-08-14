/* NavHub Service Worker：离线壳 + 静态资源缓存 */
const CACHE = 'navhub-v1'
const PRECACHE = ['/', '/manifest.webmanifest', '/icon-192.png', '/icon-512.png']

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting())
  )
})

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
  )
})

self.addEventListener('fetch', (e) => {
  const url = new URL(e.request.url)
  // API 请求不缓存，直连网络
  if (url.pathname.startsWith('/api/')) return
  // 只缓存同源 GET
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return

  e.respondWith(
    caches.match(e.request).then((cached) => {
      const fetched = fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone()
            caches.open(CACHE).then((c) => c.put(e.request, clone))
          }
          return resp
        })
        .catch(() => cached)
      return cached || fetched
    })
  )
})
