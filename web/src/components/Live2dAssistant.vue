<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { createWidget } from 'l2d-widget'
import { api } from '../api'

const props = defineProps({
  isAdmin: { type: Boolean, default: true }, // false = 访客：仅聊天，不能添加
})
const emit = defineEmits(['saved'])

const boxRef = ref(null)
const stageRef = ref(null)
let widget = null
let rootEl = null
let l2d = null

// 位置（fixed 全局可拖）
const pos = ref({ x: null, y: null }) // null = 默认右下角
const dragging = ref(false)
const dragStart = { x: 0, y: 0, px: 0, py: 0 }

// 状态
const panelOpen = ref(false)
const panelTab = ref('chat') // chat | classify
const working = ref(false) // AI 处理中
const running = ref(false) // 跑动中

// 气泡
const line = ref('')
const lineVisible = ref(false)
let lineTimer = null
let randomTimer = null
let runTimer = null
let weatherTimer = null

// ---------- 聊天 ----------
const chatMsgs = ref([]) // { role: 'bot'|'user', text }
const chatInput = ref('')
const chatBusy = ref(false)

function say(text, ms = 4000) {
  line.value = text
  lineVisible.value = true
  clearTimeout(lineTimer)
  lineTimer = setTimeout(() => { lineVisible.value = false }, ms)
}

function pushBot(text) {
  chatMsgs.value.push({ role: 'bot', text })
  say(text)
}

// 本地关键词
const TIME = ['时间', '几点', '几点了', '现在几点', '报时']
const WEA = ['天气', '气温', '温度', '冷不冷', '热不热', '下雨', '会不会下雨', '怎么样']

function nowText() {
  const d = new Date()
  const wd = ['日', '一', '二', '三', '四', '五', '六'][d.getDay()]
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return { text: `现在是 ${hh}:${mm}，星期${wd}～`, hour: d.getHours() }
}

async function replyWeather() {
  chatBusy.value = true
  working.value = true
  try {
    const w = await api.weather()
    if (w.error) {
      pushBot('天气服务暂时抽风了，等会儿再问我吧～')
    } else {
      const emoji = w.code === 0 ? '☀️' : ['☁️', '🌧️', '❄️', '⛈️'][Math.floor(Math.random() * 4)]
      pushBot(`${emoji} ${w.city}现在 ${w.desc}，${w.temp}°C，湿度 ${w.humidity}%，风速 ${w.wind} km/h。${w.temp >= 33 ? '好热，记得补水！' : w.temp <= 10 ? '天冷，多穿点～' : '体感还挺舒服的～'}`)
    }
  } catch {
    pushBot('哎呀，天气没问到，晚点再试试？')
  } finally {
    chatBusy.value = false
    working.value = false
  }
}

// 聊天回复：时间/天气走本地规则，其余走 AI
const chatHistory = ref([]) // 传给后端的对话历史

function sendChat() {
  const text = chatInput.value.trim()
  if (!text || chatBusy.value) return
  chatMsgs.value.push({ role: 'user', text })
  chatInput.value = ''
  const local = localReply(text)
  if (local === 'weather') {
    replyWeather() // 异步天气
  } else if (local) {
    chatHistory.value.push({ role: 'user', content: text })
    chatHistory.value.push({ role: 'assistant', content: local })
    setTimeout(() => pushBot(local), 400 + Math.random() * 400)
    randomMotion()
  } else {
    aiReply(text)
  }
}

async function aiReply(text) {
  chatBusy.value = true
  working.value = true
  chatHistory.value.push({ role: 'user', content: text })
  try {
    const r = await api.chat(text, chatHistory.value.slice(0, -1))
    chatHistory.value.push({ role: 'assistant', content: r.reply })
    pushBot(r.reply)
    randomMotion()
  } catch (e) {
    pushBot('哎呀，AI 暂时联系不上，等会儿再找我吧～')
  } finally {
    chatBusy.value = false
    working.value = false
  }
}

// 本地规则：时间/天气等快速回答，不浪费 AI。返回 'weather' 表示走异步天气
function localReply(text) {
  const t = (text || '').toLowerCase().trim()
  if (TIME.some(w => t.includes(w))) {
    return nowText().text
  }
  if (WEA.some(w => t.includes(w))) {
    return 'weather'
  }
  return null // 其余全部交给 AI
}

// ---------- AI 分类（仅管理员） ----------
const miniUrl = ref('')
const miniBusy = ref(false)
const miniResult = ref(null)
const miniError = ref('')
const miniPhase = ref('') // '' | 'ready' | 'saved'
const miniPick = ref(null)
const miniPickNew = ref(false)
const miniNewName = ref('')
const catNames = ref([])

// 随机台词（丰富版）
const CHATS = [
  '今天想收藏点什么呀？',
  '把好网站交给我，我帮你整理！',
  '嘿嘿，要不要试试贴个网址给我？',
  '我的分类能力可强了～',
  '收藏多了也不怕，有我在！',
  '发呆中… 需要我帮忙吗？',
  '网站太多找不到？丢给我就行！',
  '双击便签可以复制内容哦～',
  '想听现在几点吗？问我呀！',
  '外面的天气要不要帮你看看？',
  '我每天都会帮你盯着导航，放心～',
  '嘘…我在认真守护你的收藏墙！',
  '累了就双击便签放松一下！',
  '你最近收藏的网站都很有品味嘛～',
  '要不要整理一下分类？我可以帮忙！',
  '我的梦想是当全世界最好的导航助手！',
  '发现好网站记得分享给我哦～',
  '代码写累了吧？休息一下下～',
  '你猜我现在在干嘛？在等你呀！',
  '听说双击卡片也能复制，试试？',
  '今天的你也很棒！',
  '需要我跑一圈提提神吗？🏃',
]

// 随机动作（丰富版）
function randomMotion() {
  if (!l2d || working.value) return
  const actions = [
    () => { l2d.playMotion('flick_head') },
    () => { l2d.playMotion('tap_body') },
    () => { l2d.playMotion('thanking') },
    () => { l2d.playMotion('idle-01') },
    () => { l2d.playMotion('idle-02') },
    () => { l2d.playMotion('idle-03') },
    () => { l2d.setExpression && l2d.setExpression(0) },
    () => { l2d.setExpression && l2d.setExpression(1) },
  ]
  actions[Math.floor(Math.random() * actions.length)]()
}

// 定时报时间/天气（每 30~45 分钟一次）
async function periodicReport() {
  if (panelOpen.value) return
  const r = Math.random()
  try {
    if (r < 0.35) {
      const t = nowText()
      say(`${t.text}${t.hour >= 22 || t.hour < 6 ? ' 该休息啦～' : ' 今天过得怎么样？'}`)
      randomMotion()
    } else if (r < 0.6) {
      const w = await api.weather()
      if (!w.error) {
        say(`${w.city}现在 ${w.desc}，${w.temp}°C${w.temp >= 33 ? '，好热！' : ''}`)
        randomMotion()
      }
    } else {
      say(CHATS[Math.floor(Math.random() * CHATS.length)])
      randomMotion()
    }
  } catch {}
}

// 随机说话 + 动作（每 20~40 秒一次）
function startRandomLoop() {
  stopRandomLoop()
  const tick = () => {
    randomTimer = setTimeout(() => {
      if (!panelOpen.value) {
        say(CHATS[Math.floor(Math.random() * CHATS.length)])
        randomMotion()
      }
      tick()
    }, 20000 + Math.random() * 20000)
  }
  tick()
}

function stopRandomLoop() {
  clearTimeout(randomTimer)
}

// 跑动动画（沿屏幕底部小幅移动）
function startRun() {
  if (running.value) return
  running.value = true
  const stage = stageRef.value
  if (!stage) return
  const rect = stage.getBoundingClientRect()
  const maxRight = window.innerWidth - rect.width - 10
  const dir = Math.random() > 0.5 ? 1 : -1
  const dist = 60 + Math.random() * 100
  const target = Math.min(maxRight, Math.max(10, (pos.value.x !== null ? pos.value.x : window.innerWidth - rect.width - 20) + dir * dist))
  const startX = pos.value.x !== null ? pos.value.x : window.innerWidth - rect.width - 20
  const duration = 900 + Math.random() * 600
  const t0 = performance.now()

  function step(t) {
    const p = Math.min(1, (t - t0) / duration)
    const eased = p < 0.5 ? 2 * p * p : 1 - Math.pow(-2 * p + 2, 2) / 2
    pos.value.x = startX + (target - startX) * eased
    if (p < 1) requestAnimationFrame(step)
    else running.value = false
  }
  requestAnimationFrame(step)
  if (l2d) l2d.playMotion('flick_head')
}

// ---------- 挂载 Live2D ----------
async function initWidget() {
  if (!boxRef.value) return
  try {
    widget = createWidget({
      model: {
        path: 'https://model.hacxy.cn/bilibili-22/index.json',
        tips: false,
      },
      position: 'bottom-right',
      size: 240,
      primaryColor: 'rgba(0, 122, 255, 0.85)',
    })
    l2d = widget.l2d
    await nextTick()
    await new Promise((r) => setTimeout(r, 50))
    const candidates = Array.from(document.body.children).filter(
      (el) => el.tagName === 'DIV' && el.style.position === 'fixed' && el.querySelector('canvas')
    )
    rootEl = candidates[candidates.length - 1]
    if (rootEl && boxRef.value) {
      rootEl.style.position = 'absolute'
      rootEl.style.bottom = 'auto'
      rootEl.style.right = 'auto'
      rootEl.style.top = '0'
      rootEl.style.left = '0'
      rootEl.style.zIndex = '10'
      rootEl.style.pointerEvents = 'auto'
      rootEl.style.width = '100%'
      rootEl.style.height = '100%'
      boxRef.value.appendChild(rootEl)
      // 隐藏 l2d-widget 自带菜单（休眠/About 按钮），我们用自绘交互
      const btn = rootEl.querySelector('button')
      if (btn) {
        const menuWrap = btn.closest('div')
        if (menuWrap && menuWrap !== rootEl) menuWrap.style.display = 'none'
      }
    }
    if (props.isAdmin) {
      say('你好呀，我是你的导航助手，把我拖到喜欢的位置吧！')
    } else {
      say('你好呀，我是导航助手～想聊聊天或者问时间天气都可以！')
    }
    startRandomLoop()
    // 每 30~45 分钟主动报时间/天气
    const sched = () => {
      weatherTimer = setTimeout(async () => {
        await periodicReport()
        sched()
      }, 30 * 60 * 1000 + Math.random() * 15 * 60 * 1000)
    }
    sched()
  } catch (e) {
    console.warn('Live2D init failed:', e)
  }
}

// ---------- 拖拽 ----------
function stageStyle() {
  if (pos.value.x !== null && pos.value.y !== null) {
    return { left: pos.value.x + 'px', top: pos.value.y + 'px', right: 'auto', bottom: 'auto' }
  }
  return {}
}

function onMouseDown(e) {
  if (e.target.closest('.l2d-panel') || e.target.closest('.l2d-bubble') || e.target.closest('.l2d-stage__menu')) return
  dragging.value = true
  const rect = stageRef.value.getBoundingClientRect()
  dragStart.x = e.clientX
  dragStart.y = e.clientY
  dragStart.px = pos.value.x !== null ? pos.value.x : rect.left
  dragStart.py = pos.value.y !== null ? pos.value.y : rect.top
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
}

function onMouseMove(e) {
  if (!dragging.value) return
  pos.value.x = dragStart.px + (e.clientX - dragStart.x)
  pos.value.y = dragStart.py + (e.clientY - dragStart.y)
}

function onMouseUp() {
  dragging.value = false
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
}

// ---------- 点击机器人 → 弹小窗 ----------
function togglePanel() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value && miniPhase.value === 'saved') {
    miniUrl.value = ''
    miniResult.value = null
    miniPhase.value = ''
    miniError.value = ''
  }
  if (!panelOpen.value) {
    // 关掉时重新开始随机说话
    startRandomLoop()
  } else {
    stopRandomLoop()
  }
}

async function miniClassify() {
  if (!miniUrl.value.trim()) return
  miniBusy.value = true
  working.value = true
  miniError.value = ''
  miniResult.value = null
  miniPick.value = null
  miniPickNew.value = false
  miniNewName.value = ''
  say('让我看看这个网站…')
  try {
    const r = await api.classify(miniUrl.value.trim())
    miniResult.value = r
    miniPhase.value = 'ready'
    const sug = r.suggestion
    if (sug.category) {
      miniPick.value = sug.category
      miniPickNew.value = false
    } else if (sug.new_category) {
      miniPickNew.value = true
      miniNewName.value = sug.new_category
    } else {
      miniPick.value = null
      miniPickNew.value = false
    }
    if (sug.category) {
      say(`我觉得它适合「${sug.category}」！确认后我就添加～`)
      l2d && l2d.playMotion('thanking')
    } else if (sug.new_category) {
      say(`建议新建「${sug.new_category}」分类！确认后我就添加～`)
    } else {
      say('嗯…拿不准，你帮我选一个分类吧')
    }
  } catch (e) {
    miniError.value = e.message
    say('哎呀，出错了，换个网址试试？')
  } finally {
    miniBusy.value = false
    working.value = false
  }
}

async function miniConfirmSave() {
  if (!miniResult.value) return
  const isNew = miniPickNew.value
  const categoryName = isNew ? (miniNewName.value.trim() || '未分类') : miniPick.value
  if (!categoryName) return
  miniBusy.value = true
  try {
    const page = miniResult.value.page
    let categoryId = null
    let newName = null
    if (isNew) newName = categoryName
    else {
      const cats = await api.categories()
      const hit = cats.find((c) => c.name === categoryName)
      if (hit) categoryId = hit.id
      else newName = categoryName
    }
    await api.aiSave({
      url: page.url,
      title: page.title,
      description: (page.description || (miniResult.value.suggestion && miniResult.value.suggestion.description) || ''),
      tags: (miniResult.value.suggestion && miniResult.value.suggestion.tags) || '',
      favicon: page.favicon,
      category_id: categoryId,
      new_category: newName,
    })
    miniPhase.value = 'saved'
    say('保存好啦！🎉')
    l2d && l2d.playMotion('thanking')
    emit('saved') // 通知主界面刷新
  } catch (e) {
    miniError.value = e.message
    say('哎呀，保存失败了…')
  } finally {
    miniBusy.value = false
  }
}

function miniCancel() {
  miniPhase.value = ''
  miniResult.value = null
  miniUrl.value = ''
  miniError.value = ''
  miniPick.value = null
  miniPickNew.value = false
}

// ---------- 面板拖拽调大小（右下角手柄 + 右/下边缘都可拖） ----------
const panelSize = ref({ w: 290, h: null }) // null = 高度自适应
let resizing = false
const resizeStart = { x: 0, y: 0, w: 290, h: 0, mode: 'se' }

function onResizeDown(e, mode = 'se') {
  if (e.button !== 0) return
  resizing = true
  resizeStart.x = e.clientX
  resizeStart.y = e.clientY
  resizeStart.w = panelSize.value.w
  resizeStart.h = panelSize.value.h || 340
  resizeStart.mode = mode
  e.preventDefault()
  e.stopPropagation()
  window.addEventListener('mousemove', onResizeMove)
  window.addEventListener('mouseup', onResizeUp)
}

function onResizeMove(e) {
  if (!resizing) return
  const dw = e.clientX - resizeStart.x
  const dh = e.clientY - resizeStart.y
  if (resizeStart.mode === 'e' || resizeStart.mode === 'se') {
    panelSize.value.w = Math.min(520, Math.max(240, resizeStart.w + dw))
  }
  if (resizeStart.mode === 's' || resizeStart.mode === 'se') {
    panelSize.value.h = Math.min(560, Math.max(260, resizeStart.h + dh))
  }
}

function onResizeUp() {
  resizing = false
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeUp)
}

onMounted(async () => {
  await initWidget()
  try {
    const cats = await api.categories()
    catNames.value = cats.map((c) => c.name)
  } catch {}
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('mousemove', onResizeMove)
  window.removeEventListener('mouseup', onResizeUp)
  clearTimeout(lineTimer)
  stopRandomLoop()
  clearTimeout(weatherTimer)
  if (widget && widget.destroy) widget.destroy()
  widget = null
  if (rootEl) rootEl.remove()
})
</script>

<template>
  <div ref="stageRef" class="l2d-stage" :class="{ dragging, running }" :style="stageStyle()" @mousedown="onMouseDown">
    <!-- 说话气泡 -->
    <div class="l2d-bubble" :class="{ visible: lineVisible && !panelOpen }">{{ line }}</div>

    <!-- 机器人画布 -->
    <div ref="boxRef" class="l2d-canvas-box" @click="togglePanel" :class="{ working }">
      <div v-if="working" class="l2d-work-glow"></div>
    </div>

    <!-- 小菜单：跑动 -->
    <div class="l2d-stage__menu">
      <button class="l2d-menu-btn" @click.stop="startRun" title="跑动一下">🏃</button>
    </div>

    <!-- 处理小窗 -->
    <div v-if="panelOpen" class="l2d-panel card" :style="{ width: panelSize.w + 'px', height: panelSize.h ? panelSize.h + 'px' : undefined }">
      <div class="l2d-panel__head">
        <span>🧡 导航助手</span>
        <button class="l2d-panel__close" @click="panelOpen = false">✕</button>
      </div>

      <!-- Tab 切换 -->
      <div class="l2d-panel__tabs">
        <button class="l2d-tab" :class="{ active: panelTab === 'chat' }" @click="panelTab = 'chat'">💬 聊天</button>
        <button v-if="isAdmin" class="l2d-tab" :class="{ active: panelTab === 'classify' }" @click="panelTab = 'classify'">🏷️ 分类添加</button>
      </div>

      <div class="l2d-panel__body">
        <!-- 聊天 Tab（所有登录用户） -->
        <template v-if="panelTab === 'chat'">
          <div class="l2d-chat">
            <div v-if="chatMsgs.length === 0" class="l2d-chat__empty">
              <div>来聊聊天吧～ 问我时间、天气都可以！</div>
              <div style="display: flex; flex-wrap: wrap; gap: 4px; margin-top: 6px;">
                <button v-for="q in ['现在几点？', '今天天气怎么样？', '你是谁？', '你好呀']" :key="q" class="chip" @click="chatInput = q; sendChat()">{{ q }}</button>
              </div>
            </div>
            <div v-for="(m, i) in chatMsgs" :key="i" class="l2d-chat__msg" :class="m.role">
              <span class="l2d-chat__bubble">{{ m.text }}</span>
            </div>
          </div>
          <div class="l2d-chat__input">
            <input v-model="chatInput" class="input" placeholder="说点什么…" @keyup.enter="sendChat" :disabled="chatBusy" />
            <button class="btn btn-primary btn-sm" @click="sendChat" :disabled="chatBusy || !chatInput.trim()">发送</button>
          </div>
        </template>

        <!-- 分类添加 Tab（仅管理员） -->
        <template v-else>
          <template v-if="miniPhase === '' || miniPhase === 'saved'">
            <input
              v-model="miniUrl"
              class="input"
              placeholder="粘贴网址，比如 https://github.com"
              @keyup.enter="miniClassify"
              :disabled="miniBusy"
            />
            <button class="btn btn-primary" @click="miniClassify" :disabled="miniBusy" style="width: 100%; justify-content: center;">
              {{ miniBusy ? '分析中…' : '帮我分类' }}
            </button>
            <div v-if="miniPhase === 'saved'" class="l2d-panel__ok">✅ 已保存！还可以继续添加</div>
          </template>

          <template v-else-if="miniPhase === 'ready' && miniResult">
            <div class="l2d-panel__site">
              <span class="favicon"><img :src="miniResult.page.favicon" @error="$event.target.style.display = 'none'" /></span>
              <div style="min-width: 0;">
                <div class="l2d-panel__title">{{ miniResult.page.title }}</div>
                <div class="subtitle">{{ miniResult.page.description || '无描述' }}</div>
              </div>
            </div>
            <div class="l2d-panel__suggest">
              <b v-if="miniResult.suggestion.category">🎯 AI 建议：「{{ miniResult.suggestion.category }}」</b>
              <b v-else-if="miniResult.suggestion.new_category">💡 AI 建议新建：「{{ miniResult.suggestion.new_category }}」</b>
              <b v-else>🤔 AI 没把握，你来选</b>
              <span class="subtitle">{{ miniResult.suggestion.reason }} · 置信度 {{ Math.round((miniResult.suggestion.confidence || 0) * 100) }}%</span>
              <span v-if="miniResult.suggestion.tags" class="l2d-panel__tags">
                <span v-for="t in miniResult.suggestion.tags.split(',')" :key="t" class="chip mini-tag">{{ t }}</span>
              </span>
            </div>
            <div class="subtitle">确认要添加到哪个分类？</div>
            <div class="l2d-panel__chips">
              <button
                v-for="n in catNames"
                :key="n"
                class="chip"
                :class="{ selected: !miniPickNew && miniPick === n }"
                @click="miniPickNew = false; miniPick = n"
              >{{ n }}</button>
              <button class="chip" :class="{ selected: miniPickNew }" @click="miniPickNew = true; miniPick = null">＋ 新建分类</button>
            </div>
            <input
              v-if="miniPickNew"
              v-model="miniNewName"
              class="input"
              placeholder="新分类名称"
            />
            <div class="l2d-panel__actions">
              <button class="btn btn-sm" @click="miniCancel">取消</button>
              <button
                class="btn btn-sm btn-primary"
                @click="miniConfirmSave"
                :disabled="miniBusy || (!miniPick && !miniPickNew) || (miniPickNew && !miniNewName.trim())"
              >{{ miniBusy ? '添加中…' : '✅ 确认添加' }}</button>
            </div>
          </template>

          <div v-if="miniError" class="l2d-panel__err">{{ miniError }}</div>
        </template>
      </div>

      <!-- 拖拽调大小：右边缘 / 下边缘 / 右下角手柄 -->
      <div class="l2d-panel__edge l2d-panel__edge-r" @mousedown="onResizeDown($event, 'e')" title="拖动调宽度"></div>
      <div class="l2d-panel__edge l2d-panel__edge-s" @mousedown="onResizeDown($event, 's')" title="拖动调高度"></div>
      <div class="l2d-panel__resize" title="拖动调整大小" @mousedown="onResizeDown($event, 'se')">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v6h-6M15 21l6-6M3 9v-6h6M9 3l-6 6"/></svg>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 全局机器人：fixed 右下角，可自由拖拽 */
.l2d-stage {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 190px;
  height: 210px;
  user-select: none;
  z-index: 9999;
  cursor: grab;
  transition: transform 0.5s ease;
}
.l2d-stage.dragging { cursor: grabbing; }

/* 跑动：左右晃动 + 轻微弹跳 */
.l2d-stage.running { animation: l2d-run 0.4s ease-in-out infinite; }
@keyframes l2d-run {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  25% { transform: translateY(-4px) rotate(-2deg); }
  75% { transform: translateY(-4px) rotate(2deg); }
}

.l2d-canvas-box {
  position: relative;
  width: 100%;
  height: 100%;
  cursor: pointer;
}
.l2d-stage.dragging .l2d-canvas-box { cursor: grabbing; }

/* 处理中动作：弹跳 + 光晕 */
.l2d-canvas-box.working { animation: l2d-bounce 0.6s ease-in-out infinite; }
@keyframes l2d-bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
.l2d-work-glow {
  position: absolute;
  inset: 0;
  pointer-events: none;
  border-radius: var(--radius-lg);
  box-shadow: inset 0 0 30px rgba(0, 122, 255, 0.3);
  animation: l2d-pulse 1.2s ease-in-out infinite;
  z-index: 5;
}
@keyframes l2d-pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

/* 小菜单 */
.l2d-stage__menu {
  position: absolute;
  top: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  z-index: 20;
}
.l2d-menu-btn {
  width: 26px;
  height: 26px;
  border-radius: var(--radius-full);
  border: 1px solid var(--border);
  background: var(--bg-surface);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-card);
}
.l2d-menu-btn:hover { background: var(--bg-hover); }
.l2d-menu-btn.active { border-color: var(--primary); background: var(--bg-selected); }

/* 气泡 */
.l2d-bubble {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 50%;
  transform: translateX(-50%) translateY(6px);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  padding: 8px 12px;
  font-size: 12px;
  color: var(--text-secondary);
  max-width: 220px;
  opacity: 0;
  transition: opacity 0.3s, transform 0.3s;
  pointer-events: none;
  z-index: 12;
}
.l2d-bubble::after {
  content: '';
  position: absolute;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  border: 6px solid transparent;
  border-top-color: var(--bg-surface);
}
.l2d-bubble.visible {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

/* 面板 */
.l2d-panel {
  position: absolute;
  right: 0;
  bottom: calc(100% + 10px);
  width: 290px;
  padding: 0;
  z-index: 30;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  min-width: 240px;
  min-height: 260px;
}
.l2d-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  font-size: 13px;
  font-weight: 600;
  border-bottom: 1px solid var(--border);
  background: var(--bg-sidebar);
}
.l2d-panel__close {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  color: var(--text-tertiary);
}
.l2d-panel__close:hover { color: var(--text-primary); }

/* Tabs */
.l2d-panel__tabs {
  display: flex;
  gap: 2px;
  padding: 6px 8px 0;
  border-bottom: 1px solid var(--border);
}
.l2d-tab {
  flex: 1;
  padding: 6px 0;
  border: none;
  background: none;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -1px;
}
.l2d-tab.active {
  color: var(--primary);
  border-bottom-color: var(--primary);
  font-weight: 600;
}

/* 面板内容 */
.l2d-panel__body {
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

/* 拖拽调大小：右下角手柄（带图标，明显） */
.l2d-panel__resize {
  position: absolute;
  right: 0;
  bottom: 0;
  width: 22px;
  height: 22px;
  cursor: nwse-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-tertiary);
  background: var(--bg-muted);
  border-top-left-radius: 8px;
  opacity: 0.8;
  z-index: 5;
}
.l2d-panel__resize:hover {
  color: var(--primary);
  background: var(--bg-selected);
  opacity: 1;
}

/* 边缘拖拽条 */
.l2d-panel__edge {
  position: absolute;
  z-index: 4;
}
.l2d-panel__edge-r {
  top: 0;
  right: 0;
  width: 8px;
  height: 100%;
  cursor: ew-resize;
}
.l2d-panel__edge-s {
  left: 0;
  bottom: 0;
  width: 100%;
  height: 8px;
  cursor: ns-resize;
}

/* 聊天 */
.l2d-chat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
  padding: 2px;
}
.l2d-chat__empty {
  font-size: 12px;
  color: var(--text-tertiary);
  text-align: center;
  padding: 12px 4px;
}
.l2d-chat__msg {
  display: flex;
  align-items: flex-end;
  gap: 4px;
}
.l2d-chat__msg.bot { justify-content: flex-start; }
.l2d-chat__msg.user { justify-content: flex-end; }
.l2d-chat__bubble {
  max-width: 85%;
  padding: 6px 10px;
  border-radius: var(--radius-md);
  font-size: 12px;
  line-height: 1.5;
  word-break: break-word;
  user-select: text; /* 允许鼠标拖选复制 */
  -webkit-user-select: text;
  cursor: text;
}
.l2d-chat__msg.bot .l2d-chat__bubble {
  background: var(--bg-muted);
  border: 1px solid var(--border);
  color: var(--text-primary);
  border-top-left-radius: 2px;
}
.l2d-chat__msg.user .l2d-chat__bubble {
  background: var(--primary);
  color: var(--primary-foreground);
  border-top-right-radius: 2px;
}
.l2d-chat__input {
  display: flex;
  gap: 6px;
}
.l2d-chat__input .input { flex: 1; }

/* 分类添加 */
.l2d-panel__site {
  display: flex;
  gap: 8px;
  align-items: center;
}
.l2d-panel__title {
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.l2d-panel__suggest {
  background: var(--bg-muted);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px;
  font-size: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.l2d-panel__tags { display: flex; flex-wrap: wrap; gap: 4px; }
.l2d-panel__chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  max-height: 100px;
  overflow-y: auto;
}
.l2d-panel__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.l2d-panel__ok {
  text-align: center;
  font-size: 13px;
  color: var(--text-success, #059669);
  padding: 4px 0;
}
.l2d-panel__err {
  font-size: 12px;
  color: var(--text-danger);
  padding: 4px 0;
}

/* chip */
.chip {
  border: 1px solid var(--border);
  background: var(--bg-surface);
  border-radius: var(--radius-full);
  padding: 3px 10px;
  font-size: 12px;
  cursor: pointer;
}
.chip.selected {
  border-color: var(--primary);
  background: var(--bg-selected);
  color: var(--primary);
  font-weight: 600;
}
.mini-tag {
  font-size: 10px;
  color: var(--primary);
  background: var(--bg-selected);
  border: 1px solid color-mix(in srgb, var(--primary) 25%, transparent);
  padding: 1px 7px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .l2d-stage {
    width: 150px;
    height: 170px;
    right: 10px;
    bottom: 10px;
  }
  .l2d-panel {
    width: 260px;
    right: 0;
  }
}
</style>
