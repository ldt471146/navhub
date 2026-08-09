# NavHub · 个人网站导航

一个自托管的个人网站导航系统：AI 自动分类、标签管理、拖拽排序、便签、服务器监控，还有一只会聊天的二次元看板娘。

## 功能亮点

- 🗂️ **网站导航**：分类管理、网站卡片、拖拽排序、标签过滤、全局搜索
- ✨ **AI 自动分类**：粘贴 URL，AI 自动判断分类、写描述、打综合标签
- 🤖 **Live2D 看板娘**：可拖拽的二次元助手，随机说话/动作，支持 AI 聊天（基于你的收藏推荐网站）、报时间、报天气
- 🗒️ **便签**：彩色便利贴墙，拖拽排序、双击复制
- 🔐 **双密码双权限**：管理员密码全功能；访客密码只读（可配置开放便签/监控/机器人聊天）
- 📊 **服务器监控**：CPU/内存/磁盘/网络实时面板
- 🌗 **双主题**：浅色/深色一键切换
- 📱 **响应式**：桌面 + 移动端（侧栏抽屉）

## 技术栈

- 后端：Python FastAPI + SQLite（零外部依赖数据库）
- 前端：Vue 3 + Vite（主包 ~30KB gzip）
- AI：任意 OpenAI 兼容接口（DeepSeek / OpenAI / 中转站均可）
- 看板娘：l2d-widget（Live2D Cubism）
- 天气：open-meteo（免费，无需 key）

## 快速开始

### 1. 克隆并安装

```bash
git clone https://github.com/<your-name>/navhub.git
cd navhub

# 后端
cd server
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 前端构建
cd ../web
npm install
npm run build
```

### 2. 配置环境变量

| 变量 | 说明 | 默认值 |
|---|---|---|
| `NAVHUB_PASSWORD` | 管理员密码（**必须修改**） | `admin123456` |
| `NAVHUB_VIEWER_PASSWORD` | 访客只读密码 | `viewer123456` |
| `NAVHUB_PORT` | 后端端口 | `8001` |
| `NAVHUB_AI_BASE_URL` | OpenAI 兼容接口地址 | `https://api.openai.com/v1` |
| `NAVHUB_AI_MODEL` | 模型名 | `deepseek-chat` |
| `NAVHUB_AI_API_KEY` | API Key（不配置则禁用 AI 功能） | 空 |
| `NAVHUB_WEATHER_LAT/LON/CITY` | 天气城市坐标 | 香港 |

### 3. 启动

```bash
cd server
NAVHUB_PASSWORD=your_admin_password \
NAVHUB_VIEWER_PASSWORD=your_viewer_password \
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

浏览器打开 `http://127.0.0.1:8001`，输入管理员密码进入。

### 4. 生产部署（nginx + systemd）

见 `deploy/` 目录的示例配置：

```bash
# systemd 服务
cp deploy/navhub.service.example /etc/systemd/system/navhub.service
# 编辑里面的密码/路径后：
systemctl daemon-reload && systemctl enable --now navhub

# nginx 反向代理 + HTTPS（certbot 自动签发）
cp deploy/nginx.conf.example /etc/nginx/sites-available/navhub
```

## AI 功能说明

- **AI 分类**：输入 URL → AI 判断最合适的分类、生成描述、打标签（20 个综合大类白名单）
- **AI 聊天**：看板娘聊天会带上你收藏的网站列表作为上下文，可以问「推荐个看电影的网站」得到基于你收藏的回答
- 不配置 `NAVHUB_AI_API_KEY` 时，AI 功能自动降级为纯本地（分类手动选、聊天用规则回复）

## 双密码权限

- **管理员密码**：全部功能（增删改、拖拽、便签、监控、AI 添加）
- **访客密码**：默认只读导航（可看、可跳转），通过环境变量之外的开关可开放便签/监控/机器人聊天
- 权限在后端强制校验，前端隐藏只是体验层

## 项目结构

```
navhub/
├── server/          # FastAPI 后端
│   ├── main.py      # 路由 + 认证 + 权限
│   ├── auth.py      # 双密码 + SQLite session
│   ├── db.py        # SQLite 数据层（分类/网站/便签）
│   ├── ai.py        # AI 分类 + 聊天
│   ├── fetch.py     # 页面信息抓取 + favicon 兜底
│   └── sysinfo.py   # 系统监控采集
├── web/             # Vue 3 前端
│   └── src/
│       ├── App.vue  # 主界面（滑动分屏导航）
│       └── components/
│           ├── Live2dAssistant.vue  # 看板娘（聊天/AI分类/天气）
│           └── MonitorView.vue      # 服务器监控
└── deploy/          # systemd/nginx 部署示例
```

## License

MIT
