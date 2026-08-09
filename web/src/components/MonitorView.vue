<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { api } from '../api'

const stats = ref(null)
const loading = ref(true)
const error = ref('')
let timer = null

async function refresh() {
  try {
    stats.value = await api.systemStats()
    error.value = ''
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function fmtBytes(b) {
  if (!b && b !== 0) return '-'
  for (const unit of ['B', 'KB', 'MB', 'GB', 'TB']) {
    if (b < 1024 || unit === 'TB') return b.toFixed(1) + ' ' + unit
    b /= 1024
  }
}

function pctClass(p) {
  if (p >= 90) return 'danger'
  if (p >= 70) return 'warn'
  return 'ok'
}

onMounted(() => {
  refresh()
  timer = setInterval(refresh, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div class="monitor">
    <!-- 头部 -->
    <div class="monitor-header">
      <div>
        <div class="page-title">服务器状态</div>
        <div class="subtitle">{{ stats ? `${stats.hostname} · ${stats.arch} · 运行 ${stats.uptime}` : '加载中…' }}</div>
      </div>
      <button class="btn" @click="refresh" :disabled="loading">↻ 刷新</button>
    </div>

    <div v-if="error" class="monitor-error">{{ error }}</div>

    <template v-if="stats">
      <!-- 概览卡片行 -->
      <div class="stat-row">
        <div class="card stat-card">
          <div class="stat-icon">🧠</div>
          <div class="stat-label">CPU 使用率</div>
          <div class="stat-value" :class="pctClass(stats.cpu.percent)">{{ stats.cpu.percent }}%</div>
          <div class="progress"><div class="progress-bar" :class="pctClass(stats.cpu.percent)" :style="{ width: stats.cpu.percent + '%' }"></div></div>
          <div class="stat-meta">{{ stats.cpu.cores }} 核心 · 负载 {{ stats.cpu.load.join(' / ') }}</div>
        </div>

        <div class="card stat-card">
          <div class="stat-icon">💾</div>
          <div class="stat-label">内存</div>
          <div class="stat-value" :class="pctClass(stats.memory.percent)">{{ stats.memory.percent }}%</div>
          <div class="progress"><div class="progress-bar" :class="pctClass(stats.memory.percent)" :style="{ width: stats.memory.percent + '%' }"></div></div>
          <div class="stat-meta">{{ stats.fmt.mem_used }} / {{ stats.fmt.mem_total }}</div>
        </div>

        <div class="card stat-card">
          <div class="stat-icon">📀</div>
          <div class="stat-label">磁盘 /</div>
          <div class="stat-value" :class="pctClass(stats.disk.percent)">{{ stats.disk.percent }}%</div>
          <div class="progress"><div class="progress-bar" :class="pctClass(stats.disk.percent)" :style="{ width: stats.disk.percent + '%' }"></div></div>
          <div class="stat-meta">{{ stats.fmt.disk_used }} / {{ stats.fmt.disk_total }} · 剩余 {{ stats.fmt.disk_free }}</div>
        </div>

        <div class="card stat-card">
          <div class="stat-icon">🔄</div>
          <div class="stat-label">交换分区</div>
          <div class="stat-value" :class="pctClass(stats.swap.percent)">{{ stats.swap.percent }}%</div>
          <div class="progress"><div class="progress-bar" :class="pctClass(stats.swap.percent)" :style="{ width: stats.swap.percent + '%' }"></div></div>
          <div class="stat-meta">{{ fmtBytes(stats.swap.used) }} / {{ fmtBytes(stats.swap.total) }}</div>
        </div>
      </div>

      <!-- 每核心 + 网络/进程 -->
      <div class="two-col">
        <div class="card panel">
          <div class="section-title" style="padding: 14px 16px 10px;">CPU 每核心</div>
          <div class="core-grid">
            <div v-for="(p, i) in stats.cpu.per_core" :key="i" class="core-item">
              <span class="core-label">核 {{ i + 1 }}</span>
              <div class="progress core-progress">
                <div class="progress-bar" :class="pctClass(p)" :style="{ width: p + '%' }"></div>
              </div>
              <span class="core-val" :class="pctClass(p)">{{ p }}%</span>
            </div>
          </div>
        </div>

        <div class="card panel">
          <div class="section-title" style="padding: 14px 16px 10px;">网络与进程</div>
          <div class="net-list">
            <div class="net-item">
              <span class="net-label">📤 累计发送</span>
              <span class="net-val">{{ stats.fmt.net_sent }}</span>
            </div>
            <div class="net-item">
              <span class="net-label">📥 累计接收</span>
              <span class="net-val">{{ stats.fmt.net_recv }}</span>
            </div>
            <div class="net-item">
              <span class="net-label">🧩 进程数</span>
              <span class="net-val">{{ stats.processes }}</span>
            </div>
            <div class="net-item">
              <span class="net-label">🕐 服务器时间</span>
              <span class="net-val">{{ stats.server_time }}</span>
            </div>
            <div class="net-item">
              <span class="net-label">🖥️ 主机名</span>
              <span class="net-val">{{ stats.hostname }}</span>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.monitor { display: flex; flex-direction: column; gap: 14px; min-height: 0; flex: 1; }
.monitor-header { display: flex; align-items: center; justify-content: space-between; padding: 12px 0 4px; }
.monitor-error { color: var(--text-danger); font-size: 13px; padding: 10px 0; }

.stat-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
@media (max-width: 1280px) { .stat-row { grid-template-columns: repeat(2, 1fr); } }

.stat-card { padding: 14px 16px; display: flex; flex-direction: column; gap: 6px; }
.stat-icon { font-size: 20px; }
.stat-label { font-size: 12px; color: var(--text-tertiary); }
.stat-value { font-size: 24px; font-weight: 600; color: var(--text-primary); }
.stat-value.ok { color: var(--text-success); }
.stat-value.warn { color: var(--text-warning); }
.stat-value.danger { color: var(--text-danger); }
.stat-meta { font-size: 11px; color: var(--text-tertiary); }

.progress { height: 6px; border-radius: 3px; background: var(--bg-muted); overflow: hidden; }
.progress-bar { height: 100%; border-radius: 3px; transition: width 0.5s ease; }
.progress-bar.ok { background: var(--text-success); }
.progress-bar.warn { background: var(--text-warning); }
.progress-bar.danger { background: var(--text-danger); }

.two-col { display: grid; grid-template-columns: 1.2fr 1fr; gap: 12px; align-items: stretch; }
@media (max-width: 960px) { .two-col { grid-template-columns: 1fr; } }
.panel { display: flex; flex-direction: column; min-height: 0; }

.core-grid { padding: 0 16px 14px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px 14px; overflow-y: auto; max-height: 240px; }
@media (max-width: 1280px) { .core-grid { grid-template-columns: repeat(3, 1fr); } }
.core-item { display: flex; align-items: center; gap: 6px; min-width: 0; }
.core-label { font-size: 11px; color: var(--text-tertiary); flex-shrink: 0; width: 26px; }
.core-progress { flex: 1; }
.core-val { font-size: 11px; color: var(--text-secondary); flex-shrink: 0; width: 38px; text-align: right; }

.net-list { padding: 0 16px 14px; display: flex; flex-direction: column; }
.net-item { display: flex; justify-content: space-between; align-items: center; padding: 9px 0; border-bottom: 1px solid var(--border); }
.net-item:last-child { border-bottom: none; }
.net-label { font-size: 13px; color: var(--text-secondary); }
.net-val { font-size: 13px; color: var(--text-primary); font-weight: 500; }
</style>
