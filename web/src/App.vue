<script setup>
import { ref, computed, watch, onMounted, nextTick, defineAsyncComponent } from 'vue'
import {
  Compass, LayoutGrid, Settings, NotebookPen, Activity, Eye, Tags,
  FolderOpen, StickyNote, Pencil, Download, Upload, Search, Plus,
  LogOut, Star, Trash2, TriangleAlert, Globe, Menu, X, CheckCircle2,
  Sparkles, ChevronDown, Zap, MessageCircle, Heart, Wand2, Palette,
  Database, Flame, Clock, Send, Bot, Ruler, MoreHorizontal, ArrowUpRight,
  Moon, Sun, Pin, Folder, Monitor, Newspaper, Tv, Clapperboard, Video,
  Gamepad2, BookOpen, ShoppingCart, Plane, Wallet, CreditCard, Wrench,
  Brain, Lightbulb, Music, Headphones, Mic, Guitar, Piano, Drum, Camera,
  Cloud, Gem, Gift, PartyPopper, Pizza, Hamburger, Coffee, Home, Building2,
  School, Hospital, Landmark, Store, Car, Bike, Ship, Rocket, Map, Calendar,
  CalendarDays, BarChart3, TrendingUp, TrendingDown, MessagesSquare,
  Satellite, Package, BatteryCharging, Tag, FlaskConical, Microscope,
  GraduationCap, User, Users, PenLine, Trophy, Target, Archive, Contact,
  Magnet, ScrollText, Printer, Phone, Code2, Keyboard, MousePointer2,
  Smartphone, Save, Dices, CheckSquare, KeyRound, Copy, RefreshCw,
} from 'lucide-vue-next'
import { api, ApiError } from './api'
import MonitorView from './components/MonitorView.vue'
import ParticleBg from './components/ParticleBg.vue'

// ---------- 分类图标体系：lucide SVG 优先，兼容历史 emoji ----------
const ICON_CHOICES = [
  { name: 'folder', comp: Folder }, { name: 'folder-open', comp: FolderOpen },
  { name: 'rocket', comp: Rocket }, { name: 'bot', comp: Bot },
  { name: 'monitor', comp: Monitor }, { name: 'code', comp: Code2 },
  { name: 'globe', comp: Globe }, { name: 'brain', comp: Brain },
  { name: 'lightbulb', comp: Lightbulb }, { name: 'sparkles', comp: Sparkles },
  { name: 'zap', comp: Zap }, { name: 'flame', comp: Flame },
  { name: 'star', comp: Star }, { name: 'heart', comp: Heart },
  { name: 'gem', comp: Gem }, { name: 'trophy', comp: Trophy },
  { name: 'target', comp: Target }, { name: 'book-open', comp: BookOpen },
  { name: 'graduation-cap', comp: GraduationCap }, { name: 'microscope', comp: Microscope },
  { name: 'flask', comp: FlaskConical }, { name: 'music', comp: Music },
  { name: 'headphones', comp: Headphones }, { name: 'mic', comp: Mic },
  { name: 'piano', comp: Piano }, { name: 'guitar', comp: Guitar },
  { name: 'film', comp: Clapperboard }, { name: 'tv', comp: Tv },
  { name: 'camera', comp: Camera }, { name: 'newspaper', comp: Newspaper },
  { name: 'gamepad', comp: Gamepad2 }, { name: 'palette', comp: Palette },
  { name: 'wrench', comp: Wrench }, { name: 'settings', comp: Settings },
  { name: 'package', comp: Package }, { name: 'shopping-cart', comp: ShoppingCart },
  { name: 'wallet', comp: Wallet }, { name: 'credit-card', comp: CreditCard },
  { name: 'home', comp: Home }, { name: 'building', comp: Building2 },
  { name: 'school', comp: School }, { name: 'hospital', comp: Hospital },
  { name: 'landmark', comp: Landmark }, { name: 'store', comp: Store },
  { name: 'car', comp: Car }, { name: 'bike', comp: Bike },
  { name: 'ship', comp: Ship }, { name: 'plane', comp: Plane },
  { name: 'map', comp: Map }, { name: 'compass', comp: Compass },
  { name: 'clock', comp: Clock }, { name: 'calendar', comp: Calendar },
  { name: 'chart', comp: BarChart3 }, { name: 'trending-up', comp: TrendingUp },
  { name: 'message', comp: MessageCircle }, { name: 'users', comp: Users },
  { name: 'user', comp: User }, { name: 'satellite', comp: Satellite },
  { name: 'phone', comp: Phone }, { name: 'mail', comp: MessagesSquare },
  { name: 'keyboard', comp: Keyboard }, { name: 'smartphone', comp: Smartphone },
  { name: 'printer', comp: Printer }, { name: 'save', comp: Save },
  { name: 'tag', comp: Tag }, { name: 'pen', comp: PenLine },
  { name: 'archive', comp: Archive }, { name: 'magnet', comp: Magnet },
  { name: 'scroll', comp: ScrollText }, { name: 'cloud', comp: Cloud },
  { name: 'moon', comp: Moon }, { name: 'sun', comp: Sun },
]

const LUCIDE_MAP = Object.fromEntries(ICON_CHOICES.map(c => [c.name, c.comp]))

// 历史 emoji 分类 → lucide 图标（渲染时兜底 FolderOpen）
const EMOJI_ICONS = {
  '📌': Pin, '📁': Folder, '📂': FolderOpen, '🤖': Bot, '💻': Monitor,
  '🖥️': Monitor, '📰': Newspaper, '🗞️': Newspaper, '📺': Tv, '🎬': Clapperboard,
  '🎥': Video, '📹': Video, '🎮': Gamepad2, '🕹️': Gamepad2, '📚': BookOpen,
  '📖': BookOpen, '🛒': ShoppingCart, '✈️': Plane, '🛩️': Plane, '💰': Wallet,
  '💵': Wallet, '💳': CreditCard, '🎨': Palette, '🔧': Wrench, '🛠️': Wrench,
  '🧰': Wrench, '🧠': Brain, '💡': Lightbulb, '🌐': Globe, '🌍': Globe,
  '🌎': Globe, '🌏': Globe, '🔥': Flame, '⭐': Star, '❤️': Heart,
  '🎵': Music, '🎧': Headphones, '🎤': Mic, '🎙️': Mic, '🎸': Guitar,
  '🎹': Piano, '🥁': Drum, '🎻': Music, '📷': Camera, '☁️': Cloud,
  '🌙': Moon, '☀️': Sun, '⚡': Zap, '💎': Gem, '🎁': Gift,
  '🎉': PartyPopper, '🎊': PartyPopper, '🍕': Pizza, '🍔': Hamburger, '☕': Coffee,
  '🏠': Home, '🏢': Building2, '🏫': School, '🏥': Hospital, '🏦': Landmark,
  '🏪': Store, '🚗': Car, '🚕': Car, '🚲': Bike, '🛵': Bike, '🚢': Ship,
  '🚀': Rocket, '🛸': Rocket, '🗺️': Map, '🧭': Compass, '⏰': Clock,
  '🗓️': Calendar, '📅': Calendar, '📆': CalendarDays, '📊': BarChart3,
  '📈': TrendingUp, '📉': TrendingDown, '💬': MessageCircle, '🗣️': MessagesSquare,
  '📡': Satellite, '⚙️': Settings, '📦': Package, '🔋': BatteryCharging,
  '🔍': Search, '🔎': Search, '🏷️': Tag, '✨': Sparkles, '🧪': FlaskConical,
  '🔬': Microscope, '🎓': GraduationCap, '👤': User, '👥': Users,
  '📝': PenLine, '✍️': PenLine, '✏️': PenLine, '🏆': Trophy, '🥇': Trophy,
  '🎯': Target, '🗄️': Archive, '📇': Contact, '🧲': Magnet, '📜': ScrollText,
  '🖨️': Printer, '☎️': Phone, '📞': Phone, '🧑‍💻': Code2, '👨‍💻': Code2,
  '👩‍💻': Code2, '⌨️': Keyboard, '🖱️': MousePointer2, '📱': Smartphone,
  '💾': Save,
}

function catIcon(icon) {
  if (!icon) return FolderOpen
  if (EMOJI_ICONS[icon]) return EMOJI_ICONS[icon]
  if (LUCIDE_MAP[icon]) return LUCIDE_MAP[icon]
  return FolderOpen
}

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
  const body = document.body
  const mode = bgMode.value
  if (mode === 'custom' && bgUrl.value.trim()) {
    root.style.setProperty('--app-bg-image', `url(${bgUrl.value.trim()})`)
    root.style.setProperty('--app-bg-color', 'var(--bg-app)')
    body.dataset.customBg = '1'
  } else if (mode === 'color') {
    root.style.setProperty('--app-bg-image', 'none')
    root.style.setProperty('--app-bg-color', bgColor.value)
    delete body.dataset.customBg
  } else {
    root.style.setProperty('--app-bg-image', 'none')
    root.style.setProperty('--app-bg-color', 'var(--bg-app)')
    delete body.dataset.customBg
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

// ---------- A5: 网格密度 ----------
const density = ref(localStorage.getItem('navhub-density') || 'comfort') // comfort | compact
function applyDensity(d) {
  density.value = d
  localStorage.setItem('navhub-density', d)
  document.body.dataset.density = d
}
function toggleDensity() { applyDensity(density.value === 'comfort' ? 'compact' : 'comfort') }
applyDensity(density.value)

// ---------- A1: Cmd/Ctrl+K 全局命令面板 ----------
const paletteOpen = ref(false)
const paletteQuery = ref('')
const paletteIndex = ref(0)
const paletteInputRef = ref(null)
const paletteWeb = ref(null) // { answer, results } 全网搜索结果
const paletteWebBusy = ref(false)
let paletteTimer = null

// 输入防抖 400ms 后发起全网搜索（经后端代理，key 不暴露）
watch(paletteQuery, (q) => {
  clearTimeout(paletteTimer)
  paletteWeb.value = null
  const query = (q || '').trim()
  if (!query || query.startsWith('#')) return
  paletteTimer = setTimeout(async () => {
    paletteWebBusy.value = true
    try { paletteWeb.value = await api.searchWeb(query) } catch { paletteWeb.value = null }
    paletteWebBusy.value = false
  }, 400)
})

const paletteResults = computed(() => {
  const q = paletteQuery.value.trim().toLowerCase()
  const out = []
  if (!q) {
    // 空查询：快捷操作
    return [
      { type: 'action', label: 'AI 添加网站', hint: '粘贴 URL 自动分类', run: () => { paletteOpen.value = false; view.value = 'add' } },
      { type: 'action', label: '便签', hint: '', run: () => { paletteOpen.value = false; view.value = 'notes' } },
      { type: 'action', label: '服务器监控', hint: '', run: () => { paletteOpen.value = false; view.value = 'monitor' } },
      { type: 'action', label: '标签管理', hint: '', run: () => { paletteOpen.value = false; view.value = 'tags' } },
      { type: 'action', label: '切换主题', hint: theme.value === 'light' ? '切到深色' : '切到浅色', run: () => { paletteOpen.value = false; toggleTheme() } },
    ]
  }
  if (q.startsWith('#')) {
    const t = q.slice(1)
    for (const [name, n] of allTags.value) {
      if (name.toLowerCase().includes(t)) out.push({ type: 'tag', label: `#${name}`, hint: `${n} 个网站`, run: () => { paletteOpen.value = false; activeTag.value = name; goToPanel('all') } })
    }
    return out.slice(0, 8)
  }
  // 本地站点
  for (const s of sites.value) {
    const title = (s.title || '').toLowerCase()
    const url = (s.url || '').toLowerCase()
    const tags = (s.tags || '').toLowerCase()
    if (title.includes(q) || url.includes(q) || tags.includes(q)) {
      out.push({ type: 'site', label: s.title || s.url, hint: hostOf(s.url), site: s })
    }
    if (out.length >= 5) break
  }
  // 本地分类
  if (out.length < 5) {
    for (const c of categories.value) {
      if (c.name.toLowerCase().includes(q)) out.push({ type: 'cat', label: c.name, hint: `${c.site_count} 个网站`, cat: c })
      if (out.length >= 8) break
    }
  }
  // 全网搜索结果（分组标记）
  if (paletteWeb.value && paletteWeb.value.results && paletteWeb.value.results.length) {
    const webResults = paletteWeb.value.results.slice(0, 5)
    for (const r of webResults) {
      out.push({ type: 'web', label: r.title || r.url, hint: r.url, url: r.url, content: (r.content || '').slice(0, 80) })
    }
  }
  return out.slice(0, 12)
})

function openPalette() {
  paletteOpen.value = true
  paletteQuery.value = ''
  paletteIndex.value = 0
  nextTick(() => paletteInputRef.value && paletteInputRef.value.focus())
}

function closePalette() { paletteOpen.value = false }

function runPaletteItem(item) {
  if (item.type === 'site') openSite(item.site)
  else if (item.type === 'cat') goToPanel(item.cat.id)
  else if (item.type === 'web') { paletteOpen.value = false; window.open(item.url, '_blank', 'noopener') }
  else item.run && item.run()
}

function onPaletteKey(e) {
  if (e.key === 'ArrowDown') { e.preventDefault(); paletteIndex.value = (paletteIndex.value + 1) % Math.max(paletteResults.value.length, 1) }
  else if (e.key === 'ArrowUp') { e.preventDefault(); paletteIndex.value = (paletteIndex.value - 1 + Math.max(paletteResults.value.length, 1)) % Math.max(paletteResults.value.length, 1) }
  else if (e.key === 'Enter') { const it = paletteResults.value[paletteIndex.value]; if (it) runPaletteItem(it) }
  else if (e.key === 'Escape') { closePalette() }
}

// 全局快捷键
function onGlobalKey(e) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    if (loggedIn.value) openPalette()
  }
}

// ---------- B4: 批量管理 ----------
const selectMode = ref(false)
const selectedIds = ref(new Set())

function enterSelectMode() { selectMode.value = true; selectedIds.value = new Set() }
function exitSelectMode() { selectMode.value = false; selectedIds.value = new Set() }
function toggleSelect(s) {
  const set = new Set(selectedIds.value)
  if (set.has(s.id)) set.delete(s.id); else set.add(s.id)
  selectedIds.value = set
}
const selectedCount = computed(() => selectedIds.value.size)

async function bulkMoveToCat(cid) {
  if (!selectedCount.value) return
  try {
    await api.moveBulk([...selectedIds.value], cid)
    showToast(`已移动 ${selectedCount.value} 个网站`, 'info')
    exitSelectMode()
    await loadAll()
  } catch (e) { showToast(e.message, 'error') }
}

async function bulkDelete() {
  if (!selectedCount.value) return
  if (!confirm(`删除选中的 ${selectedCount.value} 个网站？`)) return
  try {
    for (const sid of selectedIds.value) await api.deleteSite(sid)
    showToast(`已删除 ${selectedCount.value} 个网站`, 'info')
    exitSelectMode()
    await loadAll()
  } catch (e) { showToast(e.message, 'error') }
}

// ---------- B6: 随机逛一个 ----------
function randomSite() {
  const list = panelSites(currentCat.value)
  if (!list.length) { showToast('当前分类没有网站', 'info'); return }
  const s = list[Math.floor(Math.random() * list.length)]
  openSite(s)
}

// ---------- B6: 最近添加排序 ----------
const sortMode = ref('default') // default | recent
const sortedSites = computed(() => {
  if (sortMode.value === 'recent') {
    return [...sites.value].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')))
  }
  return sites.value
})

// ---------- A3: 卡片 hover 网站截图预览 ----------
const previewSite = ref(null)
const previewPos = ref({ x: 0, y: 0 })
let previewTimer = null

function shotUrl(s) {
  if (!s || !s.url) return ''
  try {
    const u = new URL(s.url)
    return `https://s0.wp.com/mshots/v1/${encodeURIComponent(u.toString())}?w=640&h=400`
  } catch { return '' }
}

function showPreview(e, s) {
  if (isMobile.value) return
  clearTimeout(previewTimer)
  let x = e.clientX + 18
  if (x + 320 > window.innerWidth - 10) x = e.clientX - 338
  previewPos.value = { x, y: e.clientY + 14 }
  previewTimer = setTimeout(() => { previewSite.value = s }, 320)
}

function hidePreview() {
  clearTimeout(previewTimer)
  previewSite.value = null
}

// ---------- B7: 标签管理 ----------
const tagManage = ref({ name: '', newName: '' })
const tagModalOpen = ref(false)

function openTagManage(t) {
  tagManage.value = { name: t, newName: t }
  tagModalOpen.value = true
}

async function saveTagRename() {
  const oldName = tagManage.value.name
  const newName = tagManage.value.newName.trim()
  if (!newName) return
  try {
    const r = await api.renameTag(oldName, newName)
    showToast(`已重命名标签：${r.affected} 个网站受影响`, 'info')
    tagModalOpen.value = false
    await loadAll()
  } catch (e) { showToast(e.message, 'error') }
}

async function removeTagAll(t) {
  if (!confirm(`从所有网站移除标签 #${t}？`)) return
  try {
    const r = await api.renameTag(t, '')
    showToast(`已移除标签 #${t}（${r.affected} 个网站）`, 'info')
    if (activeTag.value === t) activeTag.value = ''
    await loadAll()
  } catch (e) { showToast(e.message, 'error') }
}

// ---------- B3: bookmarklet 收藏（#add?url=… 自动填充） ----------
const bookmarkletCode = computed(() => {
  const base = window.location.origin
  return `javascript:(function(){location.href='${base}/#add?url='+encodeURIComponent(location.href)})();`
})

// ---------- 邮箱验证码速取（第三轮） ----------
const codes = ref([])
const l2dRef = ref(null)
const latestCode = ref(null) // 新验证码 → 看板娘 prop，组件内部 watch 触发提醒（确定性）
let codesTimer = null
let codesPollStarted = false
let lastCodeNotify = ''

async function loadCodes() {
  try { codes.value = await api.mailCodes() } catch {}
}

async function pollCodesNow() {
  // 立即刷新：触发服务器即时拉取（IMAP 直连，几秒内返回）
  const btn = document.querySelector('.codes-refresh-btn')
  if (btn) { btn.dataset.busy = '1'; btn.textContent = '拉取中…' }
  try {
    await api.mailCodesPoll()
  } catch {}
  await loadCodes()
  if (btn) { delete btn.dataset.busy; btn.textContent = '立即刷新' }
}

async function pollUnreadCodes() {
  try {
    const unread = await api.mailCodesUnread()
    if (!codesPollStarted) {
      codesPollStarted = true
      if (unread.length) api.mailCodesMarkRead().catch(() => {}) // 首次静默清历史
      return
    }
    for (const c of unread) {
      const key = `${c.sender}|${c.code}|${c.mail_time}`
      if (key !== lastCodeNotify) {
        lastCodeNotify = key
        latestCode.value = { code: c.code, sender: c.sender }
      }
    }
    if (unread.length) api.mailCodesMarkRead().catch(() => {})
  } catch {}
}

async function copyCode(c) {
  try {
    await navigator.clipboard.writeText(c.code)
    showToast(`验证码 ${c.code} 已复制 ✓`, 'info')
  } catch { showToast('复制失败', 'error') }
}

async function removeCode(c) {
  if (!confirm('删除这条验证码记录？')) return
  try {
    await api.deleteMailCode(c.id)
    await loadCodes()
  } catch (e) { showToast(e.message, 'error') }
}

function parseBookmarkHash() {
  const h = window.location.hash || ''
  const m = h.match(/^#add\?url=([^&]+)/)
  if (m) {
    try {
      const url = decodeURIComponent(m[1])
      view.value = 'add'
      aiUrl.value = url
      // 自动发起分类
      setTimeout(() => classifyNow(), 300)
      history.replaceState(null, '', window.location.pathname)
    } catch {}
  }
}

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

// 面板顺序：我喜欢 → 全部 → 各分类（无未分类）
const panels = computed(() => {
  const list = [
    { key: 'likes', name: '我喜欢', icon: 'heart' },
    { key: 'all', name: '全部', icon: 'grid' },
  ]
  for (const c of categories.value) {
    list.push({ key: c.id, name: c.name, icon: c.icon || 'folder' })
  }
  return list
})

// 当前面板索引（由滑动或点击驱动）
const panelIndex = computed(() => {
  const idx = panels.value.findIndex(p => p.key === currentCat.value)
  return idx < 0 ? 0 : idx
})

// 置顶/喜欢的网站
const likedSites = computed(() => sites.value.filter(s => s.pinned))

// 每个面板内的网站（含搜索 + 标签过滤 + 排序）
function panelSites(key) {
  let list = sortedSites.value
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
  if (key === 'likes') return list.filter(s => s.pinned)
  return list.filter(s => s.category_id === key)
}

// 左侧点击分类 → 平滑滚动到对应屏（主动切换时递增动画版本号）
function goToPanel(key) {
  currentCat.value = key
  view.value = 'home'
  gridVersion.value++
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

// 标签云折叠：默认显示前 12 个，避免占满屏幕显得拥挤
const tagsExpanded = ref(false)
const visibleTags = computed(() =>
  tagsExpanded.value ? allTags.value : allTags.value.slice(0, 12)
)

// 面板切换动画版本号：key 变化触发卡片 stagger 入场重放
// 只在主动切换（goToPanel/toggleTag）时递增，滚动同步 currentCat 不触发，
// 避免 onPanelScroll 连续滚动导致所有面板 grid 反复重建
const gridVersion = ref(0)

// 点击标签过滤
function toggleTag(t) {
  activeTag.value = activeTag.value === t ? '' : t
  goToPanel('all')
}

const currentCatName = computed(() => {
  if (currentCat.value === 'likes') return '我喜欢'
  if (currentCat.value === 'all') return '全部'
  if (currentCat.value === 'uncat') return '未分类'
  const c = categories.value.find(c => c.id === currentCat.value)
  return c ? c.name : '全部'
})

// ---------- 认证 ----------
const isAdmin = ref(true) // admin=管理员全功能, viewer=访客只读
const l2dReady = ref(false) // Live2D 延迟挂载标记（3s 后为 true）

function scheduleL2d() {
  setTimeout(() => { l2dReady.value = true }, 3000)
}

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
      scheduleL2d()
      parseBookmarkHash()
    }
  } catch {}
}
onMounted(() => {
  init()
  window.addEventListener('keydown', onGlobalKey)
  // 验证码轮询：挂载即启动（每 8 秒），首次静默标记历史，后续新码提醒看板娘
  loadCodes()
  clearInterval(codesTimer)
  codesTimer = setInterval(pollUnreadCodes, 8000)
  pollUnreadCodes()
})

async function doLogin() {
  loginError.value = ''
  try {
    const r = await api.login(password.value)
    loggedIn.value = true
    isAdmin.value = r.role !== 'viewer'
    await loadAll()
    await loadNotes()
    await loadTopSites()
    scheduleL2d()
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

// 置顶/加入我喜欢
async function togglePin(s) {
  try {
    await api.togglePin(s.id, !s.pinned)
    s.pinned = s.pinned ? 0 : 1
    showToast(s.pinned ? '已加入我喜欢' : '已移出我喜欢', 'info')
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

// favicon 兜底：站点没存 → DDG 公共图标服务（存了 http 的一律升级 https，避免混合内容拦截）
function faviconUrl(s) {
  if (s.favicon) return s.favicon.replace(/^http:\/\//i, 'https://')
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

// img 加载失败：先切 DDG 兜底 → 再切 Google s2 → 都失败则隐藏
function faviconError(e, s) {
  const img = e.target
  const fb = Number(img.dataset.fallback || 0)
  if (fb === 0) {
    img.dataset.fallback = '1'
    try {
      const host = new URL(s.url).hostname
      img.src = `https://icons.duckduckgo.com/ip3/${host}.ico`
    } catch {
      img.style.display = 'none'
    }
  } else if (fb === 1) {
    img.dataset.fallback = '2'
    try {
      const host = new URL(s.url).hostname
      img.src = `https://www.google.com/s2/favicons?domain=${host}&sz=64`
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

</script>

<template>
  <!-- 登录页 -->
  <div v-if="!loggedIn" class="login-wrap">
    <div class="login-bg"></div>
    <ParticleBg />
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
    <!-- 全局二次元机器人（延迟挂载：优先保证主界面加载速度，3s 后再拉 660KB Live2D 分包） -->
    <Live2dAssistant ref="l2dRef" v-if="l2dReady" :is-admin="isAdmin" :new-code="latestCode" @saved="loadAll" />

    <!-- Toast 提示 -->
    <div v-if="toast.msg" class="toast" :class="toast.type">{{ toast.msg }}</div>

    <!-- 卡片 hover 网站截图预览（桌面端） -->
    <div v-if="previewSite && !isMobile && !selectMode" class="shot-preview" :style="{ left: previewPos.x + 'px', top: previewPos.y + 'px' }" @mouseenter="clearTimeout(previewTimer)" @mouseleave="hidePreview">
      <img v-if="shotUrl(previewSite)" :src="shotUrl(previewSite)" loading="lazy" alt="" />
      <div class="shot-preview-title">{{ previewSite.title || hostOf(previewSite.url) }}</div>
    </div>
    <!-- Cmd/Ctrl+K 全局命令面板 -->
    <Transition name="palette">
      <div v-if="paletteOpen" class="palette-mask" @click.self="closePalette">
        <div class="palette">
          <div class="palette-input-row">
            <Search :size="15" />
            <input
              ref="paletteInputRef"
              v-model="paletteQuery"
              class="palette-input"
              placeholder="搜索网站 / 分类 / 标签…   （#标签）"
              @keydown="onPaletteKey"
            />
            <kbd class="palette-kbd">ESC</kbd>
          </div>
          <div v-if="paletteResults.length" class="palette-list">
            <div v-if="paletteWebBusy" class="palette-loading"><span class="spinner" style="width: 12px; height: 12px;"></span> 正在搜索互联网…</div>
            <button
              v-for="(item, idx) in paletteResults"
              :key="idx"
              class="palette-item"
              :class="{ active: idx === paletteIndex, 'palette-item--web': item.type === 'web' }"
              @mouseenter="paletteIndex = idx"
              @click="runPaletteItem(item)"
            >
              <span class="palette-item-icon">
                <Globe v-if="item.type === 'site'" :size="14" />
                <FolderOpen v-else-if="item.type === 'cat'" :size="14" />
                <Tag v-else-if="item.type === 'tag'" :size="14" />
                <Search v-else-if="item.type === 'web'" :size="14" />
                <Zap v-else :size="14" />
              </span>
              <span class="palette-item-label">{{ item.label }}</span>
              <span class="palette-item-hint">{{ item.type === 'web' ? '全网 · ' + hostOf(item.url) : item.hint }}</span>
              <ArrowUpRight v-if="item.type === 'site' || item.type === 'web'" :size="12" class="palette-item-open" />
            </button>
          </div>
          <div v-else class="palette-empty">没有匹配的结果</div>
        </div>
      </div>
    </Transition>

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
        <button class="nav-item" :class="{ active: currentCat === 'likes' }" @click="goToPanel('likes'); closeSidebar()">
          <span class="nav-ico"><Heart :size="14" :fill="currentCat === 'likes' ? 'currentColor' : 'none'" /></span> 我喜欢
          <span class="count">{{ likedSites.length }}</span>
        </button>
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
          <span class="nav-ico" style="display: inline-flex;"><component :is="catIcon(c.icon)" :size="14" /></span>
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
          <button class="btn btn-sm" :class="{ active: view === 'tags' }" @click="view = 'tags'; closeSidebar()"><span class="btn-ico"><Tag :size="13" /></span> 标签管理</button>
          <button class="btn btn-sm" :class="{ active: view === 'codes' }" @click="view = 'codes'; closeSidebar(); loadCodes()"><span class="btn-ico"><KeyRound :size="13" /></span> 验证码</button>
          <button class="btn btn-sm" :class="{ active: view === 'monitor' }" @click="view = 'monitor'; closeSidebar()"><span class="btn-ico"><Activity :size="13" /></span> 服务器</button>
        </div>
        <div v-if="!isAdmin" class="viewer-badge"><span class="btn-ico"><Eye :size="12" /></span> 访客模式 · 导航仅可查看</div>
        <button class="btn btn-sm logout-btn" @click="doLogout"><LogOut :size="12" style="margin-right: 5px;" /> 退出登录</button>
      </div>
    </aside>

    <!-- 主内容 -->
    <main class="main">
      <div class="content">
        <!-- 视图切换：key=view 触发重建 + 进入动画（不用 out-in，避免离开动画卡死） -->
          <div class="view-root" :key="view">
        <!-- 首页视图：滑动分屏 -->
        <template v-if="view === 'home'">
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 18px 0 14px; flex-shrink: 0;">
            <div style="display: flex; align-items: center; gap: 8px; min-width: 0;">
              <button class="btn sidebar-burger" @click="toggleSidebar" title="菜单" aria-label="打开菜单">
                <Menu :size="15" />
              </button>
              <div style="min-width: 0;">
                <div class="page-title" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{{ currentCatName }}<span v-if="activeTag" class="tag-filter-hint"> · #{{ activeTag }}</span></div>
                <div class="subtitle">{{ panelSites(currentCat).length }} 个网站 · {{ isMobile ? '滑动切换分类' : '滚动鼠标滚轮切换分类' }}</div>
              </div>
            </div>
            <div v-if="isAdmin" style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap; justify-content: flex-end;">
              <button class="btn btn-sm" :class="{ active: sortMode === 'recent' }" :title="'排序：' + (sortMode === 'recent' ? '最近添加' : '默认')" @click="sortMode = sortMode === 'recent' ? 'default' : 'recent'">
                <Clock :size="12" /> {{ sortMode === 'recent' ? '最近添加' : '默认排序' }}
              </button>
              <button class="btn btn-sm" title="随机逛一个" @click="randomSite"><Dices :size="12" /> 随机</button>
              <button v-if="!selectMode" class="btn btn-sm" title="批量管理" @click="enterSelectMode"><CheckSquare :size="12" /> 批量</button>
              <button v-if="currentCat !== 'all' && currentCat !== 'uncat' && currentCat !== 'likes'" class="btn" @click="openEditCat(categories.find(c => c.id === currentCat))">
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

          <!-- 批量操作工具栏 -->
          <div v-if="selectMode" class="bulk-bar" style="flex-shrink: 0;">
            <span class="bulk-count">已选 {{ selectedCount }} 个</span>
            <select class="input bulk-cat-select" @change="bulkMoveToCat(Number($event.target.value)); $event.target.value = ''">
              <option value="">移动到分类…</option>
              <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
            </select>
            <button class="btn btn-sm btn-danger" @click="bulkDelete"><Trash2 :size="12" /> 删除</button>
            <button class="btn btn-sm" @click="exitSelectMode"><X :size="12" /> 取消</button>
          </div>

          <!-- 标签条 -->
          <div v-if="allTags.length" class="tag-bar" style="flex-shrink: 0;">
            <span class="tag-bar-label"><Tags :size="12" /></span> 标签
            <button
              v-for="[t, n] in visibleTags"
              :key="t"
              class="tag-chip"
              :class="{ active: activeTag === t }"
              @click="toggleTag(t)"
            >#{{ t }} <span class="tag-count">{{ n }}</span></button>
            <button v-if="allTags.length > 12" class="tag-more" @click="tagsExpanded = !tagsExpanded">
              {{ tagsExpanded ? '收起' : `+${allTags.length - 12} 更多` }}
            </button>
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
                <Heart v-if="p.key === 'likes'" :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
                <FolderOpen v-else :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
                <div>{{ p.key === 'likes' ? '还没有喜欢的网站，点卡片上的星标收藏' : (p.name === '全部' ? '还没有收藏网站' : '这个分类还没有网站') }}</div>
                <button v-if="isAdmin" class="btn btn-primary btn-sm" @click="view = 'add'">用 AI 添加一个</button>
              </div>
              <div v-else class="site-grid anim" :key="'g' + p.key + '-' + gridVersion">
                <div
                  v-for="(s, i) in panelSites(p.key)"
                  :key="s.id"
                  class="card site-card enter"
                  :class="{ pinned: s.pinned, 'selecting': selectMode, selected: selectedIds.has(s.id) }"
                  :style="{ animationDelay: (i % 16) * 36 + 'ms' }"
                  :draggable="isAdmin && !selectMode ? 'true' : 'false'"
                  @dragstart="isAdmin && !selectMode && onSiteDragStart(s)"
                  @dragover="isAdmin && !selectMode && onSiteDragOver($event, s)"
                  @drop="isAdmin && !selectMode && onSiteDrop"
                  @click="selectMode ? toggleSelect(s) : openSite(s)"
                  @mouseenter="showPreview($event, s)"
                  @mouseleave="hidePreview"
                >
                  <div v-if="isAdmin" class="site-card__actions">
                    <button v-if="!selectMode" class="site-act-btn" :class="{ 'pin-active': s.pinned }" :title="s.pinned ? '取消置顶' : '置顶'" @click.stop="togglePin(s)">
                      <Star :size="11" :fill="s.pinned ? 'currentColor' : 'none'" />
                    </button>
                    <button v-if="!selectMode" class="site-act-btn" title="编辑" @click.stop="openEditSite(s)">
                      <Pencil :size="11" />
                    </button>
                    <button v-if="!selectMode" class="site-act-btn danger" title="删除" @click.stop="removeSite(s)">
                      <Trash2 :size="11" />
                    </button>
                    <button v-else class="site-act-btn" :class="{ 'pin-active': selectedIds.has(s.id) }" title="选择">
                      <CheckSquare :size="11" :fill="selectedIds.has(s.id) ? 'currentColor' : 'none'" />
                    </button>
                  </div>
                  <div v-if="selectMode" class="select-check" :class="{ on: selectedIds.has(s.id) }">
                    <CheckSquare :size="13" :fill="selectedIds.has(s.id) ? 'currentColor' : 'none'" />
                  </div>
                  <div class="title">
                    <span class="favicon" :class="faviconClass(s)">
                      <img v-if="faviconUrl(s)" :src="faviconUrl(s)" loading="lazy" @error="faviconError($event, s)" />
                      <span v-if="!faviconUrl(s)"><Globe :size="14" style="color: var(--text-tertiary);" /></span>
                    </span>
                    <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ s.title || hostOf(s.url) }}</span>
                  </div>
                  <div class="desc">{{ s.description || '点击访问 ↗' }}</div>
                  <div v-if="tagList(s).length" class="site-tags">
                    <span v-for="t in tagList(s)" :key="t" class="site-tag" :class="tagClass(t)" @click.stop="toggleTag(t)">#{{ t }}</span>
                  </div>
                  <div class="meta">
                    <span v-if="s.status === 'down'" class="site-dead" title="检测于 {{ s.status_at }}"><TriangleAlert :size="10" style="vertical-align: -1px;" /> 已失效</span>
                    {{ hostOf(s.url) }}
                  </div>
                  <span class="open-arrow"><ArrowUpRight :size="13" /></span>
                </div>
              </div>
            </section>
          </div>

          <!-- 分屏指示器 -->
          <div class="panel-dots" style="flex-shrink: 0;">
            <span class="panel-counter">{{ panelIndex + 1 }} / {{ panels.length }}</span>
            <button
              v-for="(p, i) in panels"
              :key="p.key"
              class="panel-dot"
              :class="{ active: i === panelIndex }"
              :title="p.name"
              @click="goToPanel(p.key)"
            ></button>
          </div>

          <!-- 滚动提示（仅桌面） -->
          <div v-if="!isMobile" class="scroll-hint">
            <span>滚轮</span>
            <ChevronDown :size="15" />
          </div>
        </template>

        <!-- AI 添加视图 -->
        <template v-else-if="view === 'add'">
          <div style="padding: 18px 0 16px;">
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
                  ><component :is="catIcon(c.icon)" :size="12" style="vertical-align: -2px; margin-right: 3px;" /> {{ c.name }}</button>
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
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 18px 0 14px; flex-shrink: 0;">
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

        <!-- 标签管理视图 -->
        <template v-else-if="view === 'tags'">
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 18px 0 14px; flex-shrink: 0;">
            <div>
              <div class="page-title"><Tag :size="17" stroke-width="2" style="vertical-align: -2px; margin-right: 6px;" /> 标签管理</div>
              <div class="subtitle">{{ allTags.length }} 个标签 · 重命名 / 移除</div>
            </div>
          </div>
          <div class="scroll-region" style="flex: 1; padding-top: 4px;">
            <div v-if="allTags.length === 0" class="empty">
              <Tags :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
              <div>还没有标签</div>
            </div>
            <div v-else class="tag-manage-grid">
              <div v-for="[t, n] in allTags" :key="t" class="card tag-manage-item">
                <span class="tag-manage-name" :class="tagClass(t)">#{{ t }}</span>
                <span class="tag-manage-count">{{ n }} 个网站</span>
                <div class="tag-manage-actions">
                  <button class="btn btn-sm" @click="openTagManage(t)"><Pencil :size="11" /> 重命名</button>
                  <button class="btn btn-sm danger" @click="removeTagAll(t)"><Trash2 :size="11" /> 移除</button>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 邮箱验证码视图 -->
        <template v-else-if="view === 'codes'">
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 18px 0 14px; flex-shrink: 0;">
            <div>
              <div class="page-title"><KeyRound :size="17" stroke-width="2" style="vertical-align: -2px; margin-right: 6px;" /> 邮箱验证码</div>
              <div class="subtitle">自动抓取 QQ 邮箱验证码 · 每 90 秒刷新</div>
            </div>
            <button class="btn codes-refresh-btn" @click="pollCodesNow"><RefreshCw :size="13" /> 立即刷新</button>
          </div>
          <div class="scroll-region" style="flex: 1; padding-top: 4px;">
            <div v-if="codes.length === 0" class="empty">
              <KeyRound :size="34" stroke-width="1.4" style="color: var(--text-tertiary);" />
              <div>还没有验证码记录，收到验证码邮件后会自动出现在这里</div>
            </div>
            <div v-else class="code-list">
              <div v-for="c in codes" :key="c.id" class="card code-item">
                <div class="code-main">
                  <span class="code-value">{{ c.code }}</span>
                  <button class="site-act-btn" title="复制" @click="copyCode(c)"><Copy :size="12" /></button>
                  <button v-if="isAdmin" class="site-act-btn danger" title="删除" @click="removeCode(c)"><Trash2 :size="12" /></button>
                </div>
                <div class="code-meta">
                  <span v-if="c.sender" class="code-sender">{{ c.sender }}</span>
                  <span v-if="c.subject" class="code-subject">{{ c.subject }}</span>
                  <span class="code-time">{{ (c.fetched_at || c.mail_time || '').slice(5, 16) }}</span>
                </div>
              </div>
            </div>
          </div>
        </template>

        <!-- 服务器监控视图 -->
        <template v-else-if="view === 'monitor'">
          <MonitorView />
        </template>
          </div>
      </div>
    </main>

    <!-- 分类弹窗 -->
    <div v-if="showCatModal" class="modal-mask" @click.self="showCatModal = false">
      <div class="card modal">
        <div class="modal-title">{{ catModalMode === 'create' ? '新建分类' : '编辑分类' }}</div>
        <label class="modal-label">名称</label>
        <input v-model="catModalName" class="input" placeholder="如：AI 工具" autofocus />
        <label class="modal-label">图标</label>
        <div class="icon-preset">
          <button
            v-for="ic in ICON_CHOICES"
            :key="ic.name"
            class="icon-btn"
            :class="{ selected: catModalIcon === ic.name }"
            :title="ic.name"
            @click="catModalIcon = ic.name"
          ><component :is="ic.comp" :size="16" /></button>
        </div>
        <input v-model="catModalIcon" class="input" placeholder="或直接输入图标名 / emoji（如 rocket、🤖）" style="margin-top: 4px;" />
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
        <div style="display: flex; gap: 8px; margin-bottom: 6px;">
          <button v-if="isAdmin" class="btn" style="flex: 1; justify-content: center;" @click="runHealthCheck" :disabled="healthChecking">
            {{ healthChecking ? '检测中…' : '🩺 立即检测失效网站' }}
          </button>
        </div>
        <div class="modal-hint" style="margin-bottom: 14px;">服务器每 6 小时自动检测一次，失效网站自动标记「已失效」</div>

        <div class="modal-label">界面密度</div>
        <div style="display: flex; gap: 6px; margin-bottom: 14px;">
          <button class="btn btn-sm" :class="{ active: density === 'comfort' }" @click="applyDensity('comfort')">舒适</button>
          <button class="btn btn-sm" :class="{ active: density === 'compact' }" @click="applyDensity('compact')">紧凑</button>
        </div>

        <div class="modal-label">收藏到导航（书签小工具）</div>
        <div class="modal-hint" style="margin-bottom: 6px;">把下面按钮拖到浏览器书签栏，浏览任意网页时点击即可收藏到 NavHub：</div>
        <div class="bookmarklet-box">{{ bookmarkletCode }}</div>

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

    <!-- 标签重命名弹窗 -->
    <div v-if="tagModalOpen" class="modal-mask" @click.self="tagModalOpen = false">
      <div class="card modal" style="max-width: 360px;">
        <div class="modal-title"><Tag :size="13" style="vertical-align: -2px; margin-right: 4px;" /> 重命名标签</div>
        <label class="modal-label">原标签</label>
        <div class="tag-rename-old">#{{ tagManage.name }}</div>
        <label class="modal-label">新名称</label>
        <input v-model="tagManage.newName" class="input" placeholder="新标签名" @keyup.enter="saveTagRename" />
        <div class="modal-actions">
          <button class="btn" @click="tagModalOpen = false">取消</button>
          <button class="btn btn-primary" @click="saveTagRename" :disabled="!tagManage.newName.trim()">保存</button>
        </div>
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
          <option v-for="c in categories" :key="c.id" :value="c.id">{{ c.name }}</option>
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
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.92), rgba(250, 251, 253, 0.88));
  backdrop-filter: blur(18px) saturate(1.5);
  -webkit-backdrop-filter: blur(18px) saturate(1.5);
  border: 1px solid rgba(255, 255, 255, 0.85);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.95),
    0 8px 32px rgba(30, 20, 10, 0.20), 0 2px 8px rgba(30, 20, 10, 0.10),
    0 40px 120px -24px rgba(37, 99, 235, 0.18);
  animation: rise-in 0.6s var(--ease-out) both;
}
.login-logo { font-size: 40px; }
.login-title { font-size: 22px; font-weight: 600; margin-top: 8px; color: var(--text-primary); }
.login-error { color: var(--text-danger); font-size: 12px; text-align: center; }

/* 深色模式下登录卡片适配 */
[data-theme="dark"] .login-card {
  background: linear-gradient(180deg, rgba(24, 27, 33, 0.94), rgba(17, 18, 22, 0.9));
  border-color: rgba(255, 255, 255, 0.12);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06),
    0 8px 32px rgba(0, 0, 0, 0.5), 0 40px 120px -24px rgba(78, 151, 255, 0.18);
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
  padding: 5px;
  border-radius: var(--radius-sm);
  transition: background var(--dur) var(--ease-out), transform var(--dur-slow) var(--ease-spring);
}
.theme-toggle:hover { background: var(--bg-hover); transform: rotate(24deg) scale(1.08); }
.theme-toggle:active { transform: rotate(360deg) scale(0.9); }
.sidebar-search { padding: 0 12px 8px; }
.sidebar-divider { height: 1px; background: var(--border); margin: 6px 12px; }
.sidebar-footer { padding: 12px 12px 14px; border-top: 1px solid var(--border); box-shadow: inset 0 1px 0 var(--hairline); display: flex; flex-direction: column; gap: 8px; }

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
.modal {
  width: 380px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 64px);
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  background: var(--bg-surface-gradient);
  box-shadow: var(--shadow-pop), inset 0 1px 0 var(--hairline);
  animation: rise-in 0.28s var(--ease-out) both;
}
.modal-title { font-size: 15px; font-weight: 600; color: var(--text-primary); }
.modal-label { font-size: 12px; color: var(--text-tertiary); margin-top: 4px; }
.modal-hint { font-size: 11px; color: var(--text-tertiary); }
.modal-close {
  position: sticky;
  top: 0;
  align-self: flex-end;
  z-index: 5;
  margin-top: -14px;
  margin-bottom: -26px;
  width: 26px;
  height: 26px;
  border-radius: var(--radius-sm);
  background: none;
  border: none;
  color: var(--text-tertiary);
  cursor: pointer;
  font-size: 14px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease-out);
}
.modal-close:hover { color: var(--text-primary); background: var(--bg-hover); }
.modal { position: relative; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 12px; }
.icon-preset {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 156px;
  overflow-y: auto;
  padding: 2px 4px 4px 2px;
}
.icon-btn {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-muted);
  color: var(--text-secondary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease-out);
}
.icon-btn:hover { background: var(--bg-hover); color: var(--primary); transform: scale(1.1); }
.icon-btn.selected { border-color: var(--primary); background: var(--bg-selected); color: var(--primary); }

/* spinner */
.spinner {
  width: 14px; height: 14px; border: 2px solid var(--border-strong);
  border-top-color: var(--primary); border-radius: 50%;
  animation: spin 0.8s linear infinite; display: inline-block;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
