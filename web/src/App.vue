<script setup>
import { ref, computed, watch, onMounted, defineAsyncComponent } from 'vue'
import {
  Compass, LayoutGrid, Settings, NotebookPen, Activity, Eye, Tags,
  FolderOpen, StickyNote, Pencil, Download, Upload, Search, Plus,
  LogOut, Star, Trash2, TriangleAlert, Globe, Menu, X, CheckCircle2,
  Sparkles, ChevronDown, Zap, MessageCircle, Heart, Wand2, Palette,
  Database, Flame, Clock, Send, Bot, Ruler, MoreHorizontal, ArrowUpRight,
  Moon, Sun,
} from 'lucide-vue-next'
import { api, ApiError } from './api'
import MonitorView from './components/MonitorView.vue'

// ---------- 设置面板 ----------
const settingsOpen = ref(false)
const settings = ref({})
const bgMode = ref('default') // default | custom | color
const bgUrl = ref('')
const bgColor = ref('#0F172A')
const importing = ref(false)

function openSettings() {
  settingsOpen.value = true
}

async function loadSettings() {
  try {
    settings.value = await api.getSettings()
    bgMode.value = settings.value.bg_mode || 'default'
    bgUrl.value = settings.value.bg_url || ''
    bgColor.value = settings.value.bg_color || '#0F172A'
  } catch {}
}

async function saveBg() {
  try {
    await api.setSetting('bg_mode', bgMode.value)
    if (bgMode.value === 'custom') await api.setSetting('bg_url', bgUrl.value.trim())
    if (bgMode.value === 'color') await api.setSetting('bg_color', bgColor.value)
    applyBg()
    showToast('背景已保存 ✓', 'info')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

function applyBg() {
  const root = document.documentElement
  const mode = bgMode.value
  if (mode === 'custom' && bgUrl.value.trim()) {
    root.style.setProperty('--app-bg-image', `url(${bgUrl.value.trim()})`)
    root.style.setProperty('--app-bg-color', 'var(--bg-app)')
  } else if (mode === 'color') {
    root.style.setProperty('--app-bg-image', 'none')
    root.style.setProperty('--app-bg-color', bgColor.value)
  } else {
    root.style.setProperty('--app-bg-image', 'none')
    root.style.setProperty('--app-bg-color', 'var(--bg-app)')
  }
}

async function exportBackup() {
  try {
    const data = await api.exportData()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const a = document.createElement('a')
    a.href = URL.createObjectURL(blob)
    a.download = `navhub-backup-${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(a.href)
    showToast('备份已下载 ✓', 'info')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function importBackup(e) {
  const file = e.target.files[0]
  if (!file) return
  importing.value = true
  try {
    const text = await file.text()
    let data
    try {
      data = JSON.parse(text)
    } catch {
      // 尝试解析浏览器书签 HTML
      data = parseBookmarksHtml(text)
    }
    const r = await api.importData(data)
    showToast(`导入完成：分类 +${r.categories}、网站 +${r.sites}、便签 +${r.notes}`, 'info')
    await loadAll()
    await loadNotes()
  } catch (err) {
    showToast('导入失败：' + (err.message || err), 'error')
  } finally {
    importing.value = false
    e.target.value = ''
  }
}

// 解析 Netscape 书签 HTML（浏览器导出的书签）
function parseBookmarksHtml(html) {
  const cats = []
  const sites = []
  const catMap = new Map()
  // 提取 <DT><H3>分类名</H3> 和 <DT><A HREF="url">标题</A>
  const h3Re = /<H3[^>]*>([^<]+)<\/H3>/gi
  const aRe = /<A HREF="([^"]+)"[^>]*>([^<]+)<\/A>/gi
  let catId = 1
  // 按 DOM 顺序找：H3 后面的 A 属于该分类（简化：H3 与后续 A 之间）
  const sections = html.split(/<DT><H3/i)
  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i]
    const m = sec.match(/>([^<]+)<\/H3>/)
    const links = [...sec.matchAll(aRe)]
    if (m && links.length) {
      const cid = catId++
      cats.push({ id: cid, name: m[1].trim().slice(0, 20), icon: '📁' })
      for (const l of links.slice(0, 100)) {
        const url = l[1].trim()
        if (url.startsWith('http')) {
          sites.push({ id: sites.length + 1, category_id: cid, title: l[2].trim().slice(0, 60), url, description: '', tags: '' })
        }
      }
    }
  }
  // 兜底：整页所有链接
  if (!sites.length) {
    const all = [...html.matchAll(aRe)]
    for (const l of all.slice(0, 200)) {
      const url = l[1].trim()
      if (url.startsWith('http')) sites.push({ id: sites.length + 1, category_id: null, title: l[2].trim().slice(0, 60), url, description: '', tags: '' })
    }
  }
  return { categories: cats, sites, notes: [] }
}

// ---------- 热门榜 & 死链检测 ----------
const topSites = ref([])
const healthChecking = ref(false)

async function loadTopSites() {
  try { topSites.value = await api.topSites() } catch {}
}

async function runHealthCheck() {
  healthChecking.value = true
  try {
    const r = await api.healthCheck()
    showToast(`检测完成：${r.ok} 正常 / ${r.down} 失效`, r.down ? 'error' : 'info')
    await loadAll()
  } catch (e) {
    showToast(e.message || '检测失败', 'error')
  } finally {
    healthChecking.value = false
  }
}

// ---------- 便签 ----------
const notes = ref([])
const noteDraft = ref('')
const noteEditing = ref(null) // { id, content }
const dragNoteId = ref(null)
const dragOverNoteId = ref(null)

async function loadNotes() {
  notes.value = await api.notes()
}

async function saveNote() {
  const content = noteDraft.value.trim()
  if (!content) return
  try {
    await api.createNote(content)
    noteDraft.value = ''
    await loadNotes()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

// 便签拖拽排序
function onNoteDragStart(n) {
  dragNoteId.value = n.id
}

function onNoteDragOver(e, n) {
  e.preventDefault()
  if (dragNoteId.value !== null && dragNoteId.value !== n.id) {
    dragOverNoteId.value = n.id
  }
}

async function onNoteDrop() {
  const dragId = dragNoteId.value
  const overId = dragOverNoteId.value
  dragNoteId.value = null
  dragOverNoteId.value = null
  if (dragId === null || overId === null || dragId === overId) return
  // 调整顺序：把 dragId 移到 overId 的位置
  const ids = notes.value.map(x => x.id)
  const from = ids.indexOf(dragId)
  const to = ids.indexOf(overId)
  if (from < 0 || to < 0) return
  ids.splice(from, 1)
  ids.splice(to, 0, dragId)
  // 乐观更新
  const byId = {}
  notes.value.forEach(n => { byId[n.id] = n })
  notes.value = ids.map(id => byId[id])
  try {
    await api.reorderNotes(ids)
  } catch (e) {
    showToast(e.message, 'error')
    await loadNotes()
  }
}

function startEditNote(n) {
  noteEditing.value = { id: n.id, content: n.content }
}

// 双击复制便签内容
async function copyNote(n) {
  try {
    await navigator.clipboard.writeText(n.content)
    showToast('已复制到剪贴板 ✓', 'info')
  } catch {
    // 剪贴板 API 不可用时降级
    const ta = document.createElement('textarea')
    ta.value = n.content
    document.body.appendChild(ta)
    ta.select()
    document.execCommand('copy')
    document.body.removeChild(ta)
    showToast('已复制到剪贴板 ✓', 'info')
  }
}

async function saveNoteEdit() {
  if (!noteEditing.value) return
  const content = noteEditing.value.content.trim()
  if (!content) return
  try {
    await api.updateNote(noteEditing.value.id, content)
    noteEditing.value = null
    await loadNotes()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

function cancelNoteEdit() {
  noteEditing.value = null
}

async function removeNote(n) {
  if (!confirm(`删除这条便签？`)) return
  await api.deleteNote(n.id)
  if (noteEditing.value && noteEditing.value.id === n.id) noteEditing.value = null
  await loadNotes()
}

// Live2D 运行时较大，动态加载：只在进入 AI 添加页时才下载
const Live2dAssistant = defineAsyncComponent(() => import('./components/Live2dAssistant.vue'))

// ---------- 状态 ----------
const loggedIn = ref(false)
const loginError = ref('')
const password = ref('')
const categories = ref([])
const sites = ref([])
const currentCat = ref('all') // 'all' | 'uncat' | category id
const search = ref('')
const view = ref('home') // home | add | monitor
const theme = ref(localStorage.getItem('navhub-theme') || 'light')

// 弹窗状态
const showCatModal = ref(false)
const catModalMode = ref('create') // create | edit
const catModalName = ref('')
const catModalIcon = ref('')
const catEditId = ref(null)

const showSiteModal = ref(false)
const siteModalMode = ref('create') // create | edit
const siteModal = ref({ id: null, category_id: null, title: '', url: '', description: '', favicon: '', tags: '' })

// 移动端抽屉
const sidebarOpen = ref(false)

// 移动端检测（跟随视口变化）
const isMobile = ref(window.matchMedia('(max-width: 768px)').matches)
if (window.matchMedia) {
  window.matchMedia('(max-width: 768px)').addEventListener('change', e => {
    isMobile.value = e.matches
  })
}

function toggleSidebar() {
  sidebarOpen.value = !sidebarOpen.value
}

function closeSidebar() {
  sidebarOpen.value = false
}
// 拖拽排序状态
const dragCatId = ref(null)
const dragSiteId = ref(null)

// AI 分类状态
const aiUrl = ref('')
const aiBusy = ref(false)
const aiResult = ref(null) // { page, suggestion }
const aiPhase = ref('') // '' | 'classifying' | 'ready' | 'saved'
const aiError = ref('')
const aiPickCategory = ref(null) // 用户选择的分类
const aiPickNew = ref(false)
const aiNewName = ref('')

// 主题
function applyTheme(t) {
  theme.value = t
  document.documentElement.setAttribute('data-theme', t)
  localStorage.setItem('navhub-theme', t)
}
function toggleTheme() { applyTheme(theme.value === 'light' ? 'dark' : 'light') }
applyTheme(theme.value)

// ---------- 数据加载 ----------
async function loadAll() {
  const [cats, siteList] = await Promise.all([api.categories(), api.sites()])
  categories.value = cats
  sites.value = siteList
}

// 标签工具
function tagList(s) {
  return (s.tags || '').split(',').map(t => t.trim()).filter(Boolean)
}

// ---------- 滑动模式（横向分屏） ----------
const panelsRef = ref(null)
let scrollSyncing = false

// 面板顺序：全部 → 各分类（无未分类）
const panels = computed(() => {
  const list = [
    { key: 'all', name: '全部', icon: '🗂️' },
  ]
  for (const c of categories.value) {
    list.push({ key: c.id, name: c.name, icon: c.icon || '📌' })
  }
  return list
})

// 当前面板索引（由滑动或点击驱动）
const panelIndex = computed(() => {
  const idx = panels.value.findIndex(p => p.key === currentCat.value)
  return idx < 0 ? 0 : idx
})

// 每个面板内的网站（含搜索 + 标签过滤）
function panelSites(key) {
  let list = sites.value
  if (activeTag.value) list = list.filter(s => tagList(s).includes(activeTag.value))
  const q = search.value.trim().toLowerCase()
  if (q) {
    list = list.filter(s => {
      const title = (s.title || '').toLowerCase()
      const url = (s.url || '').toLowerCase()
      const tags = (s.tags || '').toLowerCase()
      if (q.startsWith('#')) {
        return tags.split(',').some(t => t.trim() && t.trim().includes(q.slice(1)))
      }
      return title.includes(q) || url.includes(q) || tags.includes(q)
    })
  }
  if (key === 'all') return list
  if (key === 'uncat') return list.filter(s => !s.category_id)
  return list.filter(s => s.category_id === key)
}

// 左侧点击分类 → 平滑滚动到对应屏
function goToPanel(key) {
  currentCat.value = key
  view.value = 'home'
  const el = panelsRef.value
  if (!el) return
  const idx = panels.value.findIndex(p => p.key === key)
  if (idx < 0) return
  scrollSyncing = true
  el.scrollTo({ top: idx * el.clientHeight, behavior: 'smooth' })
  setTimeout(() => { scrollSyncing = false }, 600)
}

// 滑动结束/进行中 → 同步左侧高亮
function onPanelScroll() {
  const el = panelsRef.value
  if (!el || scrollSyncing) return
  const idx = Math.round(el.scrollTop / el.clientHeight)
  const p = panels.value[idx]
  if (p && p.key !== currentCat.value) {
    currentCat.value = p.key
  }
}

// 全部标签（侧栏标签云）
const allTags = computed(() => {
  const map = {}
  for (const s of sites.value) {
    for (const t of tagList(s)) map[t] = (map[t] || 0) + 1
  }
  return Object.entries(map).sort((a, b) => b[1] - a[1])
})

const activeTag = ref('')

// 点击标签过滤
function toggleTag(t) {
  activeTag.value = activeTag.value === t ? '' : t
  goToPanel('all')
}

const currentCatName = computed(() => {
  if (currentCat.value === 'all') return '全部'
  if (currentCat.value === 'uncat') return '未分类'
  const c = categories.value.find(c => c.id === currentCat.value)
  return c ? c.name : '全部'
})

// ---------- 认证 ----------
const isAdmin = ref(true) // admin=管理员全功能, viewer=访客只读

// 访客只读保护：切换到访客时强制回主页（便签/服务器已开放，仅保护 AI 添加）
watch(isAdmin, v => {
  if (!v && view.value === 'add') {
    view.value = 'home'
  }
})

async function init() {
  try {
    const r = await api.me()
    if (r.ok) {
      loggedIn.value = true
      isAdmin.value = r.role !== 'viewer'
      await loadAll()
      await loadNotes()
      await loadSettings()
      await loadTopSites()
      applyBg()
    }
  } catch {}
}
onMounted(init)

async function doLogin() {
  loginError.value = ''
  try {
    const r = await api.login(password.value)
    loggedIn.value = true
    isAdmin.value = r.role !== 'viewer'
    await loadAll()
    await loadNotes()
    await loadTopSites()
  } catch (e) {
    loginError.value = e.message
  }
}

async function doLogout() {
  await api.logout()
  loggedIn.value = false
  isAdmin.value = true
  password.value = ''
  categories.value = []
  sites.value = []
}

// ---------- 分类 ----------
function openCreateCat() {
  catModalMode.value = 'create'
  catModalName.value = ''
  catModalIcon.value = ''
  catEditId.value = null
  showCatModal.value = true
}

function openEditCat(c) {
  catModalMode.value = 'edit'
  catModalName.value = c.name
  catModalIcon.value = c.icon || ''
  catEditId.value = c.id
  showCatModal.value = true
}

async function saveCategory() {
  if (!catModalName.value.trim()) return
  if (catModalMode.value === 'create') {
    await api.createCategory(catModalName.value, catModalIcon.value)
  } else {
    await api.updateCategory(catEditId.value, { name: catModalName.value, icon: catModalIcon.value })
  }
  showCatModal.value = false
  await loadAll()
}

async function removeCategory(c) {
  if (!confirm(`删除分类「${c.name}」？其中的网站会移到未分类。`)) return
  await api.deleteCategory(c.id)
  if (currentCat.value === c.id) currentCat.value = 'all'
  await loadAll()
}

// ---------- 分类拖拽排序 ----------
function onCatDragStart(c) {
  dragCatId.value = c.id
}

function onCatDragOver(e, c) {
  e.preventDefault()
  const target = c
  const dragId = dragCatId.value
  if (dragId === null || dragId === target.id) return
  const list = categories.value.map(x => ({ ...x }))
  const from = list.findIndex(x => x.id === dragId)
  const to = list.findIndex(x => x.id === target.id)
  if (from < 0 || to < 0) return
  const [moved] = list.splice(from, 1)
  list.splice(to, 0, moved)
  list.forEach((x, i) => { x.sort_order = i })
  categories.value = list
}

async function onCatDrop() {
  const dragId = dragCatId.value
  dragCatId.value = null
  if (dragId === null) return
  // 持久化新顺序
  for (const [i, c] of categories.value.entries()) {
    await api.updateCategory(c.id, { sort_order: i })
  }
  await loadAll()
}

// ---------- 网站 ----------
function openSite(s) {
  window.open(s.url, '_blank', 'noopener')
  // 点击计数（异步上报，失败忽略）
  api.clickSite(s.id).catch(() => {})
}

function openCreateSite() {
  siteModalMode.value = 'create'
  siteModal.value = {
    id: null,
    category_id: currentCat.value === 'all' || currentCat.value === 'uncat' ? null : currentCat.value,
    title: '',
    url: '',
    description: '',
    favicon: '',
    tags: '',
  }
  showSiteModal.value = true
}

function openEditSite(s) {
  siteModalMode.value = 'edit'
  siteModal.value = { ...s }
  showSiteModal.value = true
}

async function saveSite() {
  if (!siteModal.value.url.trim()) return
  try {
    if (siteModalMode.value === 'create') {
      await api.createSite({
        category_id: siteModal.value.category_id,
        title: siteModal.value.title,
        url: siteModal.value.url,
        description: siteModal.value.description,
        favicon: siteModal.value.favicon,
        tags: siteModal.value.tags,
      })
    } else {
      await api.updateSite(siteModal.value.id, {
        category_id: siteModal.value.category_id,
        title: siteModal.value.title,
        url: siteModal.value.url,
        description: siteModal.value.description,
        favicon: siteModal.value.favicon,
        tags: siteModal.value.tags,
      })
    }
    showSiteModal.value = false
    await loadAll()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

// 页面内 toast 提示（替代 alert，不会吞提示）
const toast = ref({ msg: '', type: '' })
let toastTimer = null

function showToast(msg, type = 'info') {
  toast.value = { msg, type }
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = { msg: '', type: '' } }, 3000)
}

// URL 失焦或回车时自动抓取标题/描述/logo
const siteFetching = ref(false)

async function autoFetchSite() {
  const url = siteModal.value.url.trim()
  if (!url || siteFetching.value) return
  // 已手动填了标题就不覆盖
  if (siteModal.value.title) return
  siteFetching.value = true
  try {
    const meta = await api.fetchMeta(url)
    if (meta && !siteModal.value.title) {
      if (meta.title) siteModal.value.title = meta.title
      if (meta.description) siteModal.value.description = meta.description
      if (meta.favicon) siteModal.value.favicon = meta.favicon
    }
  } catch (e) {
    // 抓取失败静默，用户可以手动填
  } finally {
    siteFetching.value = false
  }
}

// 置顶/取消置顶
async function togglePin(s) {
  try {
    await api.togglePin(s.id, !s.pinned)
    s.pinned = s.pinned ? 0 : 1
    showToast(s.pinned ? '已置顶 ⭐' : '已取消置顶', 'info')
  } catch (e) {
    showToast(e.message, 'error')
  }
}

async function removeSite(s) {
  if (!confirm(`删除「${s.title}」？`)) return
  await api.deleteSite(s.id)
  await loadAll()
}

// ---------- 网站拖拽排序 ----------
let dragSiteOrder = [] // 拖拽过程中的视觉顺序

function onSiteDragStart(s) {
  dragSiteId.value = s.id
  dragSiteOrder = panelSites(currentCat.value).map(x => x.id)
}

function onSiteDragOver(e, s) {
  e.preventDefault()
  const target = s
  const dragId = dragSiteId.value
  if (dragId === null || dragId === target.id) return
  // 仅在当前视图（同分类/全部）内排序
  const order = [...dragSiteOrder]
  const from = order.findIndex(x => x === dragId)
  const to = order.findIndex(x => x === target.id)
  if (from < 0 || to < 0) return
  const [moved] = order.splice(from, 1)
  order.splice(to, 0, moved)
  dragSiteOrder = order
  // 更新视图显示顺序
  sites.value = sites.value.map(s => {
    const idx = order.findIndex(x => x === s.id)
    if (idx >= 0) return { ...s, sort_order: idx }
    return s
  })
}

async function onSiteDrop() {
  const dragId = dragSiteId.value
  dragSiteId.value = null
  if (dragId === null) return
  // 按拖拽后的视觉顺序持久化
  for (const [i, sid] of dragSiteOrder.entries()) {
    await api.updateSite(sid, { sort_order: i })
  }
  await loadAll()
}

function moveToCat(s, cid) {
  api.updateSite(s.id, { category_id: cid }).then(loadAll)
}

// ---------- AI 分类 ----------
async function classifyNow() {
  if (!aiUrl.value.trim()) return
  aiBusy.value = true
  aiError.value = ''
  aiResult.value = null
  aiPhase.value = 'classifying'
  aiPickCategory.value = null
  aiPickNew.value = false
  aiNewName.value = ''
  try {
    const r = await api.classify(aiUrl.value.trim())
    aiResult.value = r
    const sug = r.suggestion
    if (sug.category) {
      aiPickCategory.value = sug.category
      aiPickNew.value = false
    } else if (sug.new_category) {
      aiPickNew.value = true
      aiNewName.value = sug.new_category
    } else {
      aiPickCategory.value = null
      aiPickNew.value = false
    }
    aiPhase.value = 'ready'
  } catch (e) {
    aiError.value = e.message
    aiPhase.value = ''
  } finally {
    aiBusy.value = false
  }
}

async function saveAi() {
  if (!aiResult.value) return
  const page = aiResult.value.page
  let categoryId = null
  let newName = null
  if (aiPickNew.value) {
    newName = aiNewName.value.trim() || '未分类'
  } else {
    const cat = categories.value.find(c => c.name === aiPickCategory.value)
    categoryId = cat ? cat.id : null
  }
  try {
    await api.aiSave({
      url: page.url,
      title: page.title,
      description: page.description || (aiResult.value.suggestion && aiResult.value.suggestion.description) || '',
      tags: (aiResult.value.suggestion && aiResult.value.suggestion.tags) || '',
      favicon: page.favicon,
      category_id: categoryId,
      new_category: newName,
    })
    aiPhase.value = 'saved'
    await loadAll()
  } catch (e) {
    showToast(e.message, 'error')
  }
}

function resetAi() {
  aiUrl.value = ''
  aiResult.value = null
  aiPhase.value = ''
  aiError.value = ''
  aiBusy.value = false
}

// favicon 兜底：站点没存 → DDG 公共图标服务
function faviconUrl(s) {
  if (s.favicon) return s.favicon
  try {
    const host = new URL(s.url).hostname
    return `https://icons.duckduckgo.com/ip3/${host}.ico`
  } catch {
    return ''
  }
}

// 按字符串 hash 取 0-7，分配马卡龙底色
function colorIdx(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0
  return h % 8
}

// favicon 底色 class（按域名）
function faviconClass(s) {
  return 'c' + colorIdx(hostOf(s.url))
}

// 标签色 class（按标签名）
function tagClass(t) {
  return 't' + colorIdx(t)
}

// img 加载失败：先切 DDG 兜底，DDG 也失败再隐藏
function faviconError(e, s) {
  const img = e.target
  if (!img.dataset.fallback) {
    img.dataset.fallback = '1'
    try {
      const host = new URL(s.url).hostname
      img.src = `https://icons.duckduckgo.com/ip3/${host}.ico`
    } catch {
      img.style.display = 'none'
    }
  } else {
    img.style.display = 'none'
  }
}

function hostOf(url) {
  try { return new URL(url).hostname } catch { return url }
}

const emojiPreset = [
  '📌',
  '🤖',
  '💻',
  '📰',
  '🎬',
  '🎮',
  '📚',
  '🛒',
  '✈️',
  '💰',
  '🎨',
  '🔧',
  '🧠',
  '🌐',
  '🔥',
  '⭐',
  '❤️',
  '💡',
  '🎵',
  '🎧',
  '🎤',
  '📷',
  '🎥',
  '📺',
  '🗞️',
  '📖',
  '✍️',
  '📝',
  '🧑‍💻',
  '👨‍💻',
  '👩‍💻',
  '🖥️',
  '⌨️',
  '🖱️',
  '📱',
  '💾',
  '🕹️',
  '🎯',
  '🏆',
  '🥇',
  '🚀',
  '🛰️',
  '🧪',
  '🔬',
  '🔭',
  '⚗️',
  '📊',
  '📈',
  '📉',
  '🧮',
  '🗺️',
  '🧭',
  '⏰',
  '🗓️',
  '☁️',
  '🌙',
  '☀️',
  '🌈',
  '⚡',
  '💎',
  '🔮',
  '🧿',
  '🎁',
  '🎉',
  '🍕',
  '🍔',
  '☕',
  '🍵',
  '🐱',
  '🐶',
  '🦊',
  '🐼',
  '🐧',
  '🦄',
  '🐳',
  '🐬',
  '🦋',
  '🌸',
  '🌺',
  '🍀',
  '🌿',
  '🪐',
  '👾',
  '🦾',
  '👁️',
  '🗣️',
  '💬',
  '📡',
  '🛠️',
  '⚙️',
  '🔩',
  '🧰',
  '🗄️',
  '📦',
  '🖨️',
  '📠',
  '🔌',
  '🔋',
  '🔦',
  '🏠',
  '🏢',
  '🏫',
  '🏥',
  '🏦',
  '🏪',
  '⛽',
  '🚗',
  '🚕',
  '🚲',
  '🛵',
  '🛸',
  '🛩️',
  '🚢',
  '🗽',
  '🗼',
  '🏯',
  '⛩️',
  '🎢',
  '🎡',
  '🎠',
  '⚽',
  '🏀',
  '🏈',
  '⚾',
  '🎾',
  '🏐',
  '🎱',
  '🏓',
  '🏸',
  '🥊',
  '🥋',
  '⛳',
  '🎣',
  '🏹',
  '🎳',
  '🎽',
  '🏋️',
  '🤸',
  '🧗',
  '🏄',
  '🏊',
  '🛹',
  '⛸️',
  '🎿',
  '🪂',
  '🏇',
  '🚴',
  '🧘',
  '💃',
  '🕺',
  '🎭',
  '🎪',
  '🎼',
  '🎹',
  '🥁',
  '🎷',
  '🎺',
  '🎸',
  '🪕',
  '🎻',
  '🎲',
  '♟️',
  '🀄',
  '🎴',
  '🧩',
  '🏅',
  '🎖️',
  '📯',
  '🎫',
  '🎟️',
  '📻',
  '📽️',
  '📹',
  '📼',
  '🔍',
  '🔎',
  '🧲',
  '🕯️',
  '🧴',
  '🪥',
  '🧹',
  '🧺',
  '🧻',
  '🚰',
  '🛁',
  '🚿',
  '🧼',
  '🪒',
  '🧽',
  '🪣',
  '🧯',
  '🛍️',
  '💳',
  '🏷️',
  '💸',
  '💵',
  '💴',
  '💶',
  '💷',
  '🪙',
  '🧾',
  '📜',
  '📃',
  '📄',
  '🗂️',
  '📁',
  '📂',
  '🗃️',
  '📇',
  '📍',
  '📎',
  '🖇️',
  '📏',
  '📐',
  '✂️',
  '🗒️',
  '📆',
  '📅',
  '📋',
  '📟',
  '☎️',
  '📞',
  '🎙️',
  '🕰️',
  '⏲️',
  '⏳',
  '⌛',
  '🕛',
  '🕐',
  '🕑',
  '🕒',
  '🕓',
  '🕔',
  '🕕',
  '🕖',
  '🕗',
  '🕘',
  '🕙',
  '🕚',
  '🌍',
  '🌎',
  '🌏',
  '☄️',
  '🌠',
  '🌌',
  '🌃',
  '🌆',
  '🌇',
  '🏙️',
  '🌉',
  '🌁',
  '🏞️',
  '🏔️',
  '⛰️',
  '🌋',
  '🗻',
  '🏕️',
  '🏖️',
  '🏜️',
  '🏝️',
  '🏟️',
  '🏛️',
  '🏗️',
  '🧱',
  '🪨',
  '🪵',
  '🛖',
  '🏘️',
  '🏚️',
  '🏡',
  '🛤️',
  '🛣️',
  '🛫',
  '🛬',
  '🛥️',
  '⚓',
  '🚧',
  '🚦',
  '🚥',
  '🚏',
  '🗿',
  '🏰',
  '🎇',
  '🎆',
  '✨',
  '🎈',
  '🎏',
  '🎀',
  '🎊',
  '🎃',
  '🎄',
  '🎋',
  '🎍',
  '🎎',
  '🎐',
  '🎑',
  '🎓',
  '🎒',
  '🏮',
  '🪔',
  '🧧',
  '📿',
  '🪬',
  '💠',
  '🔷',
  '🔶',
  '🔹',
  '🔸',
  '🟦',
  '🟪',
  '🟥',
  '🟧',
  '🟨',
  '🟩',
  '⬛',
  '⬜',
  '🔲',
  '🔳',
  '⚪',
  '🟫',
  '🔴',
  '🟠',
  '🟡',
  '🟢',
  '🔵',
  '🟣',
  '🔘',
  '⭕',
  '❌',
  '✅',
  '⛔',
  '🚫',
  '⚠️',
  '🚸',
  '🔞',
  '♻️',
  '💢',
  '💥',
  '💫',
  '💦',
  '💨',
  '🕳️',
  '💣',
  '💭',
  '💤',
  '🗯️',
  '🫀',
  '🫁',
  '🦴',
  '🦷',
  '👅',
  '👂',
  '👃',
  '👀',
  '💅',
  '👄',
  '🦵',
  '🦶',
  '👣',
  '👤',
  '👥',
  '🫂',
  '🧑',
  '👶',
  '👧',
  '🧒',
  '👦',
  '👩',
  '🧑‍🦰',
  '👨',
  '🧔',
  '👩‍🦰',
  '🧕',
  '👱',
  '🤱',
  '👵',
  '🧓',
  '👴',
  '🧙',
  '🧚',
  '🧛',
  '🧜',
  '🧝',
  '🧞',
  '🧟',
  '🧌',
  '🧑‍🎓',
  '👩‍🎓',
  '👨‍🎓',
  '🧑‍🏫',
  '👩‍🏫',
  '👨‍🏫',
  '🧑‍💼',
  '👩‍💼',
  '👨‍💼',
  '🧑‍🔧',
  '👩‍🔧',
  '👨‍🔧',
  '🧑‍🔬',
  '👩‍🔬',
  '👨‍🔬',
  '🧑‍⚕️',
  '👩‍⚕️',
  '👨‍⚕️',
  '🧑‍⚖️',
  '👩‍⚖️',
  '👨‍⚖️',
  '🧑‍✈️',
  '👩‍✈️',
  '👨‍✈️',
  '🧑‍🚀',
  '👩‍🚀',
  '👨‍🚀',
  '🧑‍🚒',
  '👩‍🚒',
  '👨‍🚒',
  '🧑‍🌾',
  '👩‍🌾',
  '👨‍🌾',
  '🧑‍🍳',
  '👩‍🍳',
  '👨‍🍳',
  '🕴️',
  '🧑‍🎤',
  '👩‍🎤',
  '👨‍🎤',
  '🧑‍🎨',
  '👩‍🎨',
  '👨‍🎨',
  '🧑‍🏭',
  '👩‍🏭',
  '👨‍🏭',
  '🤵',
  '👰',
  '🤰',
  '🕵️',
  '💂',
  '👮',
  '👷',
]
</script>

<template>
  <!-- 登录页 -->
  <div v-if="!loggedIn" class="login-wrap">
    <div class="login-bg"></div>
    <div class="login-mask"></div>
    <div class="card login-card">
      <div class="login-logo"><Compass :size="34" stroke-width="2.2" /></div>
      <div class="login-title">NavHub</div>
      <div class="subtitle">个人网站导航 · AI 自动分类</div>
      <form @submit.prevent="doLogin" style="width: 100%; display: flex; flex-direction: column; gap: 12px; margin-top: 20px;">
        <input v-model="password" type="password" class="input" placeholder="输入密码" autofocus />
        <button class="btn btn-primary" type="submit" style="justify-content: center;">进入导航</button>
        <div v-if="loginError" class="login-error">{{ loginError }}</div>
      </form>
    </div>
  </div>

  <!-- 主界面 -->
  <div v-else class="shell">
    <!-- 全局二次元机器人（可拖拽；管理员全功能，访客仅聊天） -->
    <Live2dAssistant :is-admin="isAdmin" @saved="loadAll" />

    <!-- Toast 提示 -->
    <div v-if="toast.msg" class="toast" :class="toast.type">{{ toast.msg }}</div>

    <!-- 移动端抽屉遮罩 -->
    <div v-if="sidebarOpen" class="drawer-mask" @click="closeSidebar"></div>

    <!-- 侧栏（移动端为抽屉） -->
    <aside class="sidebar" :class="{ open: sidebarOpen }">
      <div style="display: flex; align-items: center; gap: 8px; padding: 16px 16px 10px;">
        <Compass :size="18" />
        <span class="page-title" style="font-size: 16px;">NavHub</span>
        <button class="theme-toggle" @click="toggleTheme" :title="theme === 'light' ? '切换到深色' : '切换到浅色'">
          <Moon v-if="theme === 'light'" :size="15" />
          <Sun v-else :size="15" />
        </button>
        <button class="sidebar-close" @click="closeSidebar" title="收起">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>
        </button>
      </div>

      <div class="sidebar-search">
        <svg class="search-icon" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m21 21-4.35-4.35"/></svg>
        <input v-model="search" class="input" placeholder="搜索网站…" style="height: 28px; font-size: 12px; padding-left: 30px;" />
      </div>

      <nav class="scroll-region" style="flex: 1; padding: 6px 0;">
        <button class="nav-item" :class="{ active: currentCat === 'all' }" @click="goToPanel('all'); closeSidebar()">
          <span class="nav-ico"><LayoutGrid :size="14" /></span> 全部
          <span class="count">{{ sites.length }}</span>
        </button>
        <div class="sidebar-divider"></div>
        <div
          v-for="c in categories"
          :key="c.id"
          class="nav-item cat-item"
          :class="{ active: currentCat === c.id }"
          :draggable="isAdmin ? 'true' : 'false'"
          @dragstart="isAdmin && onCatDragStart(c)"
          @dragover="isAdmin && onCatDragOver($event, c)"
          @drop="isAdmin && onCatDrop"
          @click="goToPanel(c.id); closeSidebar()"
        >
          <span style="cursor: grab;">⠿</span>
          <span>{{ c.icon || '📌' }}</span>
          <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">{{ c.name }}</span>
          <span class="count">{{ c.site_count }}</span>
          <span v-if="isAdmin" class="cat-actions">
            <button class="cat-act-btn" title="编辑分类" @click.stop="openEditCat(c)">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
            </button>
            <button class="cat-act-btn danger" title="删除分类" @click.stop="removeCategory(c)">
              <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
            </button>
          </span>
        </div>
      </nav>

      <div class="sidebar-footer">
        <button v-if="isAdmin" class="btn btn-sm" style="width: 100%; justify-content: center;" @click="openCreateCat"><Plus :size="13" style="margin-right: 5px;" /> 新建分类</button>
        <div class="sidebar-actions">
          <button v-if="isAdmin" class="btn" @click="openSettings"><span class="btn-ico"><Settings :size="13" /></span> 设置</button>
          <button class="btn btn-sm" :class="{ active: view === 'notes' }" @click="view = 'notes'; closeSidebar()"><span class="btn-ico"><NotebookPen :size="13" /></span> 便签</button>
          <button class="btn btn-sm" :class="{ active: view === 'monitor' }" @click="view = 'monitor'; closeSidebar()"><span class="btn-ico"><Activity :size="13" /></span> 服务器</button>
        </div>
        <div v-if="!isAdmin" class="viewer-badge"><span class="btn-ico"><Eye :size="12" /></span> 访客模式 · 导航仅可查看</div>
        <button class="btn btn-sm logout-btn" @click="doLogout"><LogOut :size="12" style="margin-right: 5px;" /> 退出登录</button>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="main">
      <div class="content">
        <!-- 首页视图：滑动分屏 -->
        <template v-if="view === 'home'">
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0 10px; flex-shrink: 0;">
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
              <button class="btn sidebar-burger" @click="toggleSidebar" title="菜单" aria-label="打开菜单">
                <Menu :size="15" />
              </button>
              <div style="min-width: 0;">
                <div class="page-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ currentCatName }}<span v-if="activeTag" class="tag-filter-hint"> · #{{ activeTag }}</span></div>
                <div class="subtitle">{{ panelSites(currentCat).length }} 个网站 · {{ isMobile ? '滑动切换分类' : '滚动鼠标滚轮切换分类' }}</div>
              </div>
            </div>
            <div v-if="isAdmin" style="display: flex; gap: 8px;">
              <button v-if="currentCat !== 'all' && currentCat !== 'uncat'" class="btn" @click="openEditCat(categories.find(c => c.id === currentCat))">
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                编辑分类
              </button>
              <button class="btn" @click="view = 'notes'"><span class="btn-ico"><NotebookPen :size="13" /></span> 便签</button>
              <button class="btn btn-primary" @click="openCreateSite">
                <Plus :size="14" stroke-width="2.5" style="margin-right: 5px;" />
                手动添加
              </button>
            </div>
          </div>

          <!-- 标签条 -->
          <div v-if="allTags.length" class="tag-bar" style="flex-shrink: 0;">
            <span class="tag-bar-label"><Tags :size="12" /></span> 标签
            <button
              v-for="[t, n] in allTags"
              :key="t"
              class="tag-chip"
              :class="{ active: activeTag === t }"
              @click="toggleTag(t)"
            >#{{ t }} <span class="tag-count">{{ n }}</span></button>
            <button v-if="activeTag" class="tag-clear" @click="activeTag = ''"><X :size="11" style="vertical-align: -1px;" /> 清除</button>
          </div>

          <!-- 滑动分屏 -->
          <div class="panel-track" ref="panelsRef" @scroll="onPanelScroll">
            <section
              v-for="p in panels"
              :key="p.key"
              class="panel-page"
              :class="{ active: currentCat === p.key }"
            >
              <div v-if="panelSites(p.key).length === 0" class="empty">
                <FolderOpen :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
                <div>{{ p.name === '全部' ? '还没有收藏网站' : '这个分类还没有网站' }}</div>
                <button v-if="isAdmin" class="btn btn-primary btn-sm" @click="view = 'add'">用 AI 添加一个</button>
              </div>
              <div v-else class="site-grid">
                <div
                  v-for="s in panelSites(p.key)"
                  :key="s.id"
                  class="card site-card"
                  :class="{ pinned: s.pinned }"
                  :draggable="isAdmin ? 'true' : 'false'"
                  @dragstart="isAdmin && onSiteDragStart(s)"
                  @dragover="isAdmin && onSiteDragOver($event, s)"
                  @drop="isAdmin && onSiteDrop"
                  @click="openSite(s)"
                >
                  <div v-if="isAdmin" class="site-card__actions">
                    <button class="site-act-btn" :class="{ 'pin-active': s.pinned }" :title="s.pinned ? '取消置顶' : '置顶'" @click.stop="togglePin(s)">
                      <Star :size="11" :fill="s.pinned ? 'currentColor' : 'none'" />
                    </button>
                    <button class="site-act-btn" title="编辑" @click.stop="openEditSite(s)">
                      <Pencil :size="11" />
                    </button>
                    <button class="site-act-btn danger" title="删除" @click.stop="removeSite(s)">
                      <Trash2 :size="11" />
                    </button>
                  </div>
                  <div class="title">
                    <span class="favicon" :class="faviconClass(s)">
                      <img v-if="faviconUrl(s)" :src="faviconUrl(s)" loading="lazy" @error="faviconError($event, s)" />
                      <span v-if="!faviconUrl(s)"><Globe :size="14" style="color: var(--text-tertiary);" /></span>
                    </span>
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ s.title }}</span>
                  </div>
                  <div class="desc">{{ s.description || '暂无描述' }}</div>
                  <div v-if="tagList(s).length" class="site-tags">
                    <span v-for="t in tagList(s)" :key="t" class="site-tag" :class="tagClass(t)" @click.stop="toggleTag(t)">#{{ t }}</span>
                  </div>
                  <div class="meta">
                    <span v-if="s.status === 'down'" class="site-dead" title="检测于 {{ s.status_at }}"><TriangleAlert :size="10" style="vertical-align: -1px;" /> 已失效</span>
                    {{ hostOf(s.url) }} ↗
                  </div>
                </div>
              </div>
            </section>
          </div>

          <!-- 分屏指示器 -->
          <div class="panel-dots" style="flex-shrink: 0;">
            <button
              v-for="(p, i) in panels"
              :key="p.key"
              class="panel-dot"
              :class="{ active: i === panelIndex }"
              :title="p.name"
              @click="goToPanel(p.key)"
            ></button>
          </div>

          <!-- 滚动提示 -->
          <div class="scroll-hint">
            <span>滚轮</span>
            <ChevronDown :size="15" />
          </div>
        </template>

        <!-- AI 添加视图 -->
        <template v-else-if="view === 'add'">
          <div style="padding: 12px 0 14px;">
            <div class="page-title">AI 添加网站</div>
            <div class="subtitle">粘贴网址，AI 根据内容自动分类</div>
          </div>

          <div class="ai-layout">
            <div class="card ai-card">            
            <div class="ai-input-row">
              <input
                v-model="aiUrl"
                class="input"
                placeholder="https://example.com"
                @keyup.enter="classifyNow"
                :disabled="aiBusy"
                style="flex: 1; height: 38px;"
              />
              <button class="btn btn-primary" @click="classifyNow" :disabled="aiBusy" style="height: 38px;">
                {{ aiBusy ? '分析中…' : 'AI 分类' }}
              </button>
            </div>

            <div v-if="aiBusy" class="ai-loading">
              <span class="spinner"></span> 正在抓取网页内容并分析…
            </div>

            <div v-if="aiError" class="ai-error">{{ aiError }}</div>

            <!-- AI 结果 -->
            <div v-if="aiResult && aiPhase === 'ready'" class="ai-result">
              <div class="ai-page-info">
                <span class="favicon"><img :src="aiResult.page.favicon" @error="$event.target.style.display = 'none'" /><span v-if="!aiResult.page.favicon">🌐</span></span>
                <div style="min-width: 0;">
                  <div class="ai-title">{{ aiResult.page.title }}</div>
                  <div class="subtitle">{{ hostOf(aiResult.page.url) }}</div>
                </div>
              </div>
              <div class="ai-desc">{{ aiResult.page.description || '无描述' }}</div>

              <div class="ai-suggest" :class="{ high: (aiResult.suggestion.confidence || 0) >= 0.7 }">
                <span class="ai-badge">{{ aiResult.suggestion.category ? '🎯 建议分类' : '💡 建议新建' }}</span>
                <span class="ai-reason">{{ aiResult.suggestion.reason }}</span>
                <span class="ai-conf">置信度 {{ Math.round((aiResult.suggestion.confidence || 0) * 100) }}%</span>
              </div>
              <div v-if="aiResult.suggestion.tags" class="ai-tags">
                <span class="subtitle">标签：</span>
                <span v-for="t in aiResult.suggestion.tags.split(',')" :key="t" class="site-tag">{{ t }}</span>
              </div>

              <!-- 选择分类 -->
              <div class="ai-pick">
                <div class="subtitle" style="margin-bottom: 8px;">放入哪个分类？</div>
                <div class="ai-cat-chips">
                  <button
                    v-for="c in categories"
                    :key="c.id"
                    class="chip"
                    :class="{ selected: !aiPickNew && aiPickCategory === c.name }"
                    @click="aiPickNew = false; aiPickCategory = c.name"
                  >{{ c.icon || '📌' }} {{ c.name }}</button>
                  <button class="chip" :class="{ selected: aiPickNew }" @click="aiPickNew = true; aiPickCategory = null">
                    <Plus :size="11" style="vertical-align: -1px; margin-right: 3px;" /> 新建分类
                  </button>
                </div>
                <input
                  v-if="aiPickNew"
                  v-model="aiNewName"
                  class="input"
                  placeholder="新分类名称"
                  style="margin-top: 8px;"
                />
                <button v-if="!aiPickNew && !aiPickCategory" class="btn btn-sm" style="margin-top: 8px;" @click="aiPickNew = true">放到「未分类」</button>
              </div>

              <div class="ai-actions">
                <button class="btn" @click="resetAi">取消</button>
                <button class="btn btn-primary" @click="saveAi" :disabled="!aiPickCategory && !aiPickNew">保存</button>
              </div>
            </div>

            <div v-if="aiPhase === 'saved'" class="ai-saved">
              <CheckCircle2 :size="16" style="vertical-align: -3px; margin-right: 6px;" /> 已保存到「{{ aiPickNew ? aiNewName : aiPickCategory }}」
              <div style="margin-top: 12px; display: flex; gap: 8px;">
                <button class="btn" @click="resetAi">再添加一个</button>
                <button class="btn btn-primary" @click="view = 'home'">返回导航</button>
              </div>
            </div>
            </div>
          </div>
        </template>

        <!-- 便签视图 -->
        <template v-else-if="view === 'notes'">
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0 10px; flex-shrink: 0;">
            <div>
              <div class="page-title"><NotebookPen :size="17" stroke-width="2" style="vertical-align: -2px; margin-right: 6px;" /> 便签</div>
              <div class="subtitle">{{ notes.length }} 条 · 拖拽排序，随手记</div>
            </div>
          </div>

          <!-- 新建便签 -->
          <div class="card note-composer" style="flex-shrink: 0; background: linear-gradient(180deg, #FFF8E1, #FFFDF5); border-color: rgba(245, 158, 11, 0.25);">
            <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
              <Pencil :size="14" />
              <span style="font-size: 13px; font-weight: 600; color: #78350F;">新便签</span>
            </div>
            <textarea v-model="noteDraft" class="input" rows="2" placeholder="写点什么…" style="height: auto; padding: 10px 12px; resize: vertical; background: rgba(255, 255, 255, 0.7);" @keydown.enter.exact.prevent="saveNote"></textarea>
            <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
              <button class="btn btn-primary btn-sm" @click="saveNote" :disabled="!noteDraft.trim()">记下</button>
            </div>
          </div>

          <!-- 便签列表 -->
          <div class="scroll-region" style="flex: 1; padding-top: 10px;">
            <div v-if="notes.length === 0" class="empty">
              <StickyNote :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
              <div>还没有便签，写一条吧</div>
            </div>
            <div v-else class="site-grid" style="grid-template-columns: repeat(3, 1fr);">
              <div
                v-for="n in notes"
                :key="n.id"
                class="note-card"
                :class="[
                  'n' + colorIdx(n.content),
                  { 'note-dragging': dragNoteId === n.id, 'note-drag-over': dragOverNoteId === n.id && dragNoteId !== n.id }
                ]"
                draggable="true"
                @dragstart="onNoteDragStart(n)"
                @dragover="onNoteDragOver($event, n)"
                @drop="onNoteDrop"
                @dragend="dragNoteId = null; dragOverNoteId = null"
                @dblclick="noteEditing && noteEditing.id === n.id ? null : copyNote(n)"
                :title="'双击复制'"
              >
                <template v-if="noteEditing && noteEditing.id === n.id">
                  <div class="note-edit">
                    <textarea v-model="noteEditing.content" class="input" rows="4" style="height: auto; padding: 10px 12px; resize: vertical; background: color-mix(in srgb, var(--note-bg, #FFF8E1) 40%, var(--bg-surface));" @keydown.enter.exact.prevent="saveNoteEdit"></textarea>
                    <div style="display: flex; justify-content: flex-end; gap: 6px; margin-top: 8px;">
                      <button class="btn btn-sm" @click="cancelNoteEdit">取消</button>
                      <button class="btn btn-primary btn-sm" @click="saveNoteEdit" :disabled="!noteEditing.content.trim()">保存</button>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="note-body">
                    <div class="note-content">{{ n.content }}</div>
                    <div class="note-foot">
                      <span class="note-time">🕐 {{ (n.updated_at || n.created_at || '').slice(5, 16) }}</span>
                      <span style="display: flex; gap: 4px;">
                        <button class="site-act-btn" title="编辑" @click="startEditNote(n)" style="background: color-mix(in srgb, var(--note-bg, #FFF8E1) 30%, var(--bg-surface));">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/></svg>
                        </button>
                        <button class="site-act-btn danger" title="删除" @click="removeNote(n)" style="background: color-mix(in srgb, var(--note-bg, #FFF8E1) 30%, var(--bg-surface));">
                          <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/></svg>
                        </button>
                      </span>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </template>

        <!-- 服务器监控视图 -->
        <template v-else-if="view === 'monitor'">
          <MonitorView />
        </template>
      </div>
    </main>

    <!-- 分类弹窗 -->
    <div v-if="showCatModal" class="modal-mask" @click.self="showCatModal = false">
      <div class="card modal">
        <div class="modal-title">{{ catModalMode === 'create' ? '新建分类' : '编辑分类' }}</div>
        <label class="modal-label">名称</label>
        <input v-model="catModalName" class="input" placeholder="如：AI 工具" autofocus />
        <label class="modal-label">图标（emoji）</label>
        <input v-model="catModalIcon" class="input" placeholder="如：🤖" maxlength="4" />
        <div class="emoji-preset">
          <button v-for="e in emojiPreset" :key="e" class="emoji-btn" :class="{ selected: catModalIcon === e }" @click="catModalIcon = e">{{ e }}</button>
        </div>
        <div class="modal-actions" v-if="catModalMode === 'edit'" style="justify-content: space-between;">
          <button class="btn btn-danger" @click="removeCategory({ id: catEditId, name: catModalName }); showCatModal = false">删除分类</button>
          <div style="display: flex; gap: 8px;">
            <button class="btn" @click="showCatModal = false">取消</button>
            <button class="btn btn-primary" @click="saveCategory" :disabled="!catModalName.trim()">保存</button>
          </div>
        </div>
        <div class="modal-actions" v-else>
          <button class="btn" @click="showCatModal = false">取消</button>
          <button class="btn btn-primary" @click="saveCategory" :disabled="!catModalName.trim()">保存</button>
        </div>
      </div>
    </div>

    <!-- 设置弹窗 -->
    <div v-if="settingsOpen" class="modal-mask" @click.self="settingsOpen = false">
      <div class="card modal" style="max-width: 420px;">
        <div class="modal-title"><span class="btn-ico"><Settings :size="13" /></span> 设置</div>

        <div class="modal-label">数据备份</div>
        <div style="display: flex; gap: 8px; margin-bottom: 14px;">
          <button class="btn" style="flex: 1; justify-content: center;" @click="exportBackup"><span class="btn-ico"><Download :size="13" /></span> 导出备份</button>
          <label class="btn" style="flex: 1; justify-content: center; cursor: pointer;">
            <span class="btn-ico"><Upload :size="13" /></span> 导入{{ importing ? '中…' : '' }}
            <input type="file" accept=".json,.html,.htm" style="display: none;" @change="importBackup" />
          </label>
        </div>
        <div class="modal-hint" style="margin-bottom: 16px;">支持 NavHub JSON 备份 或 浏览器导出的书签 HTML（自动识别）</div>

        <div class="modal-label">网站健康</div>
        <div style="display: flex; gap: 8px; margin-bottom: 10px;">
          <button v-if="isAdmin" class="btn" style="flex: 1; justify-content: center;" @click="runHealthCheck" :disabled="healthChecking">
            {{ healthChecking ? '检测中…' : '🩺 立即检测失效网站' }}
          </button>
        </div>

        <div v-if="topSites.length" class="modal-label" style="margin-top: 4px;">热门网站 TOP {{ Math.min(topSites.length, 5) }}</div>
        <div v-if="topSites.length" class="top-list" style="margin-bottom: 12px;">
          <a v-for="(t, i) in topSites.slice(0, 5)" :key="t.id" class="top-item" :href="t.url" target="_blank" rel="noopener">
            <span class="top-rank">{{ i + 1 }}</span>
            <span class="top-title">{{ t.title }}</span>
            <span class="top-clicks">{{ t.clicks }} 次</span>
          </a>
        </div>

        <div class="modal-label">主页背景</div>
        <div style="display: flex; gap: 6px; margin-bottom: 10px;">
          <button class="btn btn-sm" :class="{ active: bgMode === 'default' }" @click="bgMode = 'default'">默认</button>
          <button class="btn btn-sm" :class="{ active: bgMode === 'color' }" @click="bgMode = 'color'">纯色</button>
          <button class="btn btn-sm" :class="{ active: bgMode === 'custom' }" @click="bgMode = 'custom'">图片</button>
        </div>
        <div v-if="bgMode === 'color'" style="margin-bottom: 10px;">
          <input type="color" v-model="bgColor" style="width: 48px; height: 32px; border: none; background: none; cursor: pointer;" />
        </div>
        <div v-if="bgMode === 'custom'" style="margin-bottom: 10px;">
          <input v-model="bgUrl" class="input" placeholder="图片 URL（https://…）" />
        </div>
        <button class="btn btn-primary" style="width: 100%; justify-content: center;" @click="saveBg">保存背景</button>

        <button class="modal-close" @click="settingsOpen = false">✕</button>
      </div>
    </div>

    <!-- 网站弹窗 -->
    <div v-if="showSiteModal" class="modal-mask" @click.self="showSiteModal = false">
      <div class="card modal">
        <div class="modal-title">{{ siteModalMode === 'create' ? '添加网站' : '编辑网站' }}</div>
        <label class="modal-label">URL</label>
        <div style="display: flex; gap: 6px; align-items: center;">
          <input v-model="siteModal.url" class="input" placeholder="https://…" @blur="autoFetchSite" @keyup.enter="autoFetchSite" />
          <span v-if="siteFetching" class="spinner" style="flex-shrink: 0;"></span>
          <span v-if="siteModal.favicon" class="favicon" style="flex-shrink: 0;"><img :src="siteModal.favicon" @error="$event.target.style.display = 'none'" /></span>
        </div>
        <div v-if="siteFetching" class="subtitle" style="margin-top: -6px;">正在抓取网站信息…</div>
        <label class="modal-label">标题</label>
        <input v-model="siteModal.title" class="input" placeholder="留空自动抓取" />
        <label class="modal-label">分类</label>
        <select v-model="siteModal.category_id" class="input">
          <option :value="null">未分类</option>
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.icon || '📌' }} {{ c.name }}</option>
        </select>
        <label class="modal-label">描述</label>
        <textarea v-model="siteModal.description" class="input" rows="2" placeholder="可选"></textarea>
        <label class="modal-label">标签（逗号分隔，如：AI,聊天,免费）</label>
        <input v-model="siteModal.tags" class="input" placeholder="如：AI, 工具, 教程" />
        <div v-if="siteModalMode === 'edit'" class="modal-actions" style="justify-content: space-between;">
          <button class="btn btn-danger" @click="removeSite(siteModal); showSiteModal = false">删除</button>
          <div style="display: flex; gap: 8px;">
            <button class="btn" @click="showSiteModal = false">取消</button>
            <button class="btn btn-primary" @click="saveSite" :disabled="!siteModal.url.trim()">保存</button>
          </div>
        </div>
        <div v-else class="modal-actions">
          <button class="btn" @click="showSiteModal = false">取消</button>
          <button class="btn btn-primary" @click="saveSite" :disabled="!siteModal.url.trim()">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* Toast */
.toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 200;
  padding: 10px 20px;
  border-radius: var(--radius-md);
  font-size: 13px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  color: var(--text-primary);
  animation: toast-in 0.25s ease;
  max-width: 70vw;
}

.toast.error {
  border-color: var(--text-danger);
  color: var(--text-danger);
  background: color-mix(in srgb, var(--text-danger) 6%, var(--bg-surface));
}

.toast.info {
  border-color: var(--primary);
  color: var(--primary);
}

@keyframes toast-in {
  from { opacity: 0; transform: translateX(-50%) translateY(-8px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}

/* 登录页 */
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-app);
  position: relative;
  overflow: hidden;
}

/* 背景图：cover 铺满不留白 */
.login-bg {
  position: absolute;
  inset: 0;
  background: url('./assets/login-bg.png') center/cover no-repeat;
  z-index: 0;
  animation: login-zoom 24s ease-in-out infinite alternate;
}
@keyframes login-zoom {
  from { transform: scale(1); }
  to { transform: scale(1.06); }
}
[data-theme="dark"] .login-bg {
  filter: brightness(0.9);
}

/* 柔和遮罩：保证登录框清晰可读 */
.login-mask {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(20, 16, 28, 0.25) 0%, rgba(20, 16, 28, 0.10) 45%, rgba(20, 16, 28, 0.35) 100%);
  z-index: 1;
}
[data-theme="dark"] .login-mask {
  background: linear-gradient(180deg, rgba(5, 4, 10, 0.45) 0%, rgba(5, 4, 10, 0.25) 45%, rgba(5, 4, 10, 0.5) 100%);
}

.login-card {
  width: 340px;
  padding: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  z-index: 2;
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow: 0 8px 32px rgba(30, 20, 10, 0.18), 0 2px 8px rgba(30, 20, 10, 0.08);
}
.login-logo { font-size: 40px; }
.login-title { font-size: 22px; font-weight: 600; margin-top: 8px; color: var(--text-primary); }
.login-error { color: var(--text-danger); font-size: 12px; text-align: center; }

/* 深色模式下登录卡片适配 */
[data-theme="dark"] .login-card {
  background: rgba(24, 26, 32, 0.88);
  border-color: rgba(255, 255, 255, 0.1);
}

.site-dead {
  display: inline-block;
  font-size: 10px;
  color: #DC2626;
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  border-radius: 4px;
  padding: 1px 5px;
  margin-right: 4px;
  font-weight: 600;
}

/* 热门榜 */
.top-list { display: flex; flex-direction: column; gap: 6px; }
.top-item {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px;
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: border-color 0.15s;
}
.top-item:hover { border-color: var(--primary); }
.top-rank {
  font-size: 12px; font-weight: 700;
  color: var(--primary);
  min-width: 16px; text-align: center;
}
.top-item:nth-child(1) .top-rank { color: #F59E0B; }
.top-item:nth-child(2) .top-rank { color: #94A3B8; }
.top-item:nth-child(3) .top-rank { color: #B45309; }
.top-title { font-size: 12px; font-weight: 600; color: var(--text-primary); flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.top-clicks { font-size: 11px; color: var(--text-tertiary); flex-shrink: 0; }

/* 侧栏 */
.theme-toggle {
  margin-left: auto;
  background: transparent;
  border: none;
  font-size: 16px;
  padding: 4px;
  border-radius: var(--radius-sm);
}
.theme-toggle:hover { background: var(--bg-hover); }
.sidebar-search { padding: 0 12px 8px; }
.sidebar-divider { height: 1px; background: var(--border); margin: 6px 12px; }
.sidebar-footer { padding: 12px 12px 14px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }

.viewer-badge {
  font-size: 11px;
  color: var(--text-secondary);
  background: var(--bg-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 8px;
  text-align: center;
}
.sidebar-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.sidebar-actions .btn { justify-content: center; }
.logout-btn { justify-content: center; color: var(--text-tertiary); }
.logout-btn:hover { color: var(--text-danger); }

/* AI 视图 */
.ai-layout {
  display: block;
  min-height: 0;
  flex: 1;
}
.ai-card { padding: 24px; display: flex; flex-direction: column; gap: 14px; }
.ai-input-row { display: flex; gap: 10px; }
.ai-loading { display: flex; align-items: center; gap: 10px; color: var(--text-secondary); font-size: 13px; padding: 12px 0; }
.ai-error { color: var(--text-danger); font-size: 13px; }
.ai-result { display: flex; flex-direction: column; gap: 12px; }
.ai-page-info { display: flex; align-items: center; gap: 12px; }
.ai-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.ai-desc { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }
.ai-suggest {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 12px; border-radius: var(--radius-sm);
  background: var(--bg-muted); border: 1px solid var(--border);
}
.ai-suggest.high { background: color-mix(in srgb, var(--text-success) 8%, var(--bg-surface)); border-color: color-mix(in srgb, var(--text-success) 30%, var(--border)); }
.ai-badge { font-size: 12px; font-weight: 600; color: var(--primary); flex-shrink: 0; }
.ai-reason { font-size: 13px; color: var(--text-secondary); flex: 1; }
.ai-conf { font-size: 11px; color: var(--text-tertiary); flex-shrink: 0; }
.ai-cat-chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
  height: 28px; padding: 0 12px; border-radius: var(--radius-full);
  border: 1px solid var(--border); background: var(--bg-surface);
  color: var(--text-secondary); font-size: 12px;
}
.chip:hover { background: var(--bg-hover); }
.chip.selected { background: var(--bg-selected); border-color: var(--primary); color: var(--primary); font-weight: 500; }
.ai-actions { display: flex; justify-content: flex-end; gap: 8px; padding-top: 4px; }
.ai-saved { padding: 16px 0; font-size: 14px; color: var(--text-success); }

/* 弹窗 */
.modal-mask {
  position: fixed; inset: 0; background: rgba(0, 0, 0, 0.35);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal { width: 380px; padding: 20px; display: flex; flex-direction: column; gap: 10px; }
.modal-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.modal-label { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.modal-hint { font-size: 11px; color: var(--text-tertiary); }
.modal-close { position: absolute; top: 10px; right: 12px; background: none; border: none; color: var(--text-tertiary); cursor: pointer; font-size: 14px; }
.modal-close:hover { color: var(--text-primary); }
.modal { position: relative; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.emoji-preset {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 150px;
  overflow-y: auto;
  padding-right: 4px;
}
.emoji-btn {
  width: 30px; height: 30px; border-radius: var(--radius-sm);
  border: 1px solid var(--border); background: var(--bg-muted); font-size: 15px;
}
.emoji-btn:hover { background: var(--bg-hover); }
.emoji-btn.selected { border-color: var(--primary); background: var(--bg-selected); }

/* spinner */
.spinner {
  width: 14px; height: 14px; border: 2px solid var(--border-strong);
  border-top-color: var(--primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
