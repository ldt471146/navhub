<template>
  <canvas ref="canvasRef" class="particle-bg"></canvas>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const canvasRef = ref(null)
let ctx = null
let raf = 0
let particles = []
let mouse = { x: -9999, y: -9999 }
let w = 0
let h = 0
const DPR = Math.min(window.devicePixelRatio || 1, 2)

function resize() {
  const c = canvasRef.value
  if (!c) return
  w = c.clientWidth
  h = c.clientHeight
  c.width = w * DPR
  c.height = h * DPR
  ctx = c.getContext('2d')
  ctx.scale(DPR, DPR)
  initParticles()
}

function initParticles() {
  const count = Math.min(90, Math.floor((w * h) / 16000))
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * w,
    y: Math.random() * h,
    vx: (Math.random() - 0.5) * 0.45,
    vy: (Math.random() - 0.5) * 0.45,
    r: Math.random() * 1.8 + 0.8,
  }))
}

function tick() {
  ctx.clearRect(0, 0, w, h)
  const linkDist = 130
  for (const p of particles) {
    p.x += p.vx
    p.y += p.vy
    if (p.x < 0 || p.x > w) p.vx *= -1
    if (p.y < 0 || p.y > h) p.vy *= -1
  }
  // 连线
  ctx.lineWidth = 1
  for (let i = 0; i < particles.length; i++) {
    const a = particles[i]
    for (let j = i + 1; j < particles.length; j++) {
      const b = particles[j]
      const dx = a.x - b.x
      const dy = a.y - b.y
      const d2 = dx * dx + dy * dy
      if (d2 < linkDist * linkDist) {
        const alpha = (1 - Math.sqrt(d2) / linkDist) * 0.22
        ctx.strokeStyle = `rgba(99, 132, 255, ${alpha})`
        ctx.beginPath()
        ctx.moveTo(a.x, a.y)
        ctx.lineTo(b.x, b.y)
        ctx.stroke()
      }
    }
    // 鼠标吸引
    const mdx = a.x - mouse.x
    const mdy = a.y - mouse.y
    const md2 = mdx * mdx + mdy * mdy
    if (md2 < 160 * 160) {
      a.x += (mouse.x - a.x) * 0.008
      a.y += (mouse.y - a.y) * 0.008
    }
    ctx.fillStyle = 'rgba(120, 150, 255, 0.5)'
    ctx.beginPath()
    ctx.arc(a.x, a.y, a.r, 0, Math.PI * 2)
    ctx.fill()
  }
  raf = requestAnimationFrame(tick)
}

function onMouse(e) {
  const rect = canvasRef.value.getBoundingClientRect()
  mouse.x = e.clientX - rect.left
  mouse.y = e.clientY - rect.top
}

function onLeave() {
  mouse.x = -9999
  mouse.y = -9999
}

onMounted(() => {
  resize()
  window.addEventListener('resize', resize)
  canvasRef.value.addEventListener('mousemove', onMouse)
  canvasRef.value.addEventListener('mouseleave', onLeave)
  raf = requestAnimationFrame(tick)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('resize', resize)
  if (canvasRef.value) {
    canvasRef.value.removeEventListener('mousemove', onMouse)
    canvasRef.value.removeEventListener('mouseleave', onLeave)
  }
})
</script>

<style scoped>
.particle-bg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 1;
}
</style>
