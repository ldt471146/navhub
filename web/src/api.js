// NavHub API 封装
const BASE = ''

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
  chat: (message, history) => req('POST', '/api/chat', { message, history }),
}
