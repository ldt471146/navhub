// NavHub API 封装
const BASE = ''

// 带超时的 fetch（聊天等慢接口用）
async function reqWithTimeout(method, path, body, timeoutMs = 35000) {
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const resp = await fetch(BASE + path, {
      method,
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: body !== undefined ? JSON.stringify(body) : undefined,
      signal: ctrl.signal,
    })
    if (resp.status === 401) throw new ApiError(401, '未登录')
    if (!resp.ok) {
      let detail = resp.statusText
      try {
        const data = await resp.json()
        detail = data.detail || detail
      } catch {}
      throw new ApiError(resp.status, detail)
    }
    return resp.json()
  } catch (e) {
    if (e.name === 'AbortError') throw new ApiError(408, 'AI 响应超时，稍后再试')
    throw e
  } finally {
    clearTimeout(timer)
  }
}

async function req(method, path, body) {
  const opts = {
    method,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)
  const resp = await fetch(BASE + path, opts)
  if (resp.status === 401) {
    throw new ApiError(401, '未登录')
  }
  if (!resp.ok) {
    let detail = resp.statusText
    try {
      const data = await resp.json()
      detail = data.detail || detail
    } catch {}
    throw new ApiError(resp.status, detail)
  }
  return resp.json()
}

export class ApiError extends Error {
  constructor(status, message) {
    super(message)
    this.status = status
  }
}

export const api = {
  login: (password) => req('POST', '/api/auth/login', { password }),
  me: () => req('GET', '/api/auth/me'),
  logout: () => req('POST', '/api/auth/logout'),
  categories: () => req('GET', '/api/categories'),
  createCategory: (name, icon = '') => req('POST', '/api/categories', { name, icon }),
  updateCategory: (id, patch) => req('PATCH', `/api/categories/${id}`, patch),
  deleteCategory: (id) => req('DELETE', `/api/categories/${id}`),
  sites: (categoryId) => req('GET', `/api/sites${categoryId != null ? `?category_id=${categoryId}` : ''}`),
  createSite: (site) => req('POST', '/api/sites', site),
  updateSite: (id, patch) => req('PATCH', `/api/sites/${id}`, patch),
  togglePin: (id, pinned) => req('PATCH', `/api/sites/${id}`, { pinned }),
  deleteSite: (id) => req('DELETE', `/api/sites/${id}`),
  classify: (url) => req('POST', '/api/sites/ai-classify', { url }),
  fetchMeta: (url) => req('POST', '/api/sites/fetch-meta', { url }),
  aiSave: (payload) => req('POST', '/api/sites/ai-save', payload),
  notes: () => req('GET', '/api/notes'),
  createNote: (content) => req('POST', '/api/notes', { content }),
  reorderNotes: (order) => req('POST', '/api/notes/reorder', { order }),
  updateNote: (id, content) => req('PATCH', `/api/notes/${id}`, { content }),
  deleteNote: (id) => req('DELETE', `/api/notes/${id}`),
  systemStats: () => req('GET', '/api/system/stats'),
  weather: () => req('GET', '/api/weather'),
  chat: (message, history) => reqWithTimeout('POST', '/api/chat', { message, history }),
  exportData: () => req('GET', '/api/export'),
  importData: (data) => req('POST', '/api/import', data),
  getSettings: () => req('GET', '/api/settings'),
  setSetting: (key, value) => req('POST', '/api/settings', { key, value }),
  healthCheck: () => req('POST', '/api/health-check'),
  clickSite: (site_id) => req('POST', '/api/sites/click', { site_id }),
  topSites: () => req('GET', '/api/sites/top'),
}
