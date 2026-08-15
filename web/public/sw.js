/* NavHub Service Worker v2：HTML 网络优先（保证永远最新），静态资源缓存 */
const CACHE = 'navhub-v2'
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
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return

  const isHtml = e.request.mode === 'navigate' || url.pathname === '/'

  if (isHtml) {
    // 页面：网络优先（始终最新），离线时才回退缓存
    e.respondWith(
      fetch(e.request)
        .then((resp) => {
          if (resp.ok) {
            const clone = resp.clone()
            caches.open(CACHE).then((c) => c.put(e.request, clone))
          }
          return resp
        })
        .catch(() => caches.match(e.request))
    )
    return
  }

  // 静态资源（哈希文件名）：缓存优先，后台更新
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
