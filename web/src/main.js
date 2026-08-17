import { createApp } from 'vue'
import '@fontsource-variable/inter'
import './style.css'
import App from './App.vue'

const app = createApp(App)

// 全局错误捕获（调试用，保留生产也有帮助）
app.config.errorHandler = (err, instance, info) => {
  console.error('[NAVHUB-ERROR]', err, info)
}

app.mount('#app')
