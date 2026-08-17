# NavHub · 个人网站导航

🌐 在线演示：https://nav.diecast.cloud
一个自托管的个人网站导航系统：AI 自动分类、标签管理、拖拽排序、便签、服务器监控，还有一只会聊天的二次元看板娘。

## 功能亮点

- 🗂️ **网站导航**：分类管理、网站卡片、拖拽排序、标签过滤、全局搜索
- ✨ **AI 自动分类**：粘贴 URL，AI 自动判断分类、写描述、打综合标签
- 🤖 **Live2D 看板娘**：可拖拽的二次元助手，随机说话/动作，支持 AI 聊天（基于你的收藏推荐网站，纯文字排版）、报时间、报天气；聊天面板可拖拽调整大小
- 🗒️ **便签**：彩色便利贴墙，拖拽排序、双击复制
- 🔐 **双密码双权限**：管理员密码全功能；访客密码只读（可配置开放便签/监控/机器人聊天）
- 📊 **服务器监控**：CPU/内存/磁盘/网络实时面板
- 🌗 **双主题**：浅色/深色一键切换
- 📱 **响应式**：桌面 + 移动端（侧栏抽屉）

## 技术栈

- 后端：Python FastAPI + SQLite（零外部依赖数据库）
- 前端：Vue 3 + Vite
- AI：任意 OpenAI 兼容接口（DeepSeek / OpenAI / 中转站均可）
- 看板娘：l2d-widget（Live2D Cubism）
- 天气：open-meteo（免费，无需 key）
- 验证码：QQ 邮箱 IMAP 自动抓取

## 快速开始

### 1. 克隆并安装

```bash
git clone https://github.com/ldt471146/navhub.git
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

所有配置都通过环境变量注入，**不会写死在代码里**。

| 变量 | 说明 | 示例 / 默认值 |
|---|---|---|
| `NAVHUB_PASSWORD` | 管理员密码（**必须修改**） | `your_admin_password` |
| `NAVHUB_VIEWER_PASSWORD` | 访客只读密码 | `your_viewer_password` |
| `NAVHUB_PORT` | 后端端口 | `8001` |
| `NAVHUB_AI_BASE_URL` | OpenAI 兼容 API 地址 | `https://api.deepseek.com/v1` |
| `NAVHUB_AI_MODEL` | AI 模型名 | `deepseek-v4-flash` |
| `NAVHUB_AI_API_KEY` | AI API Key（不配置则禁用 AI 功能） | `sk-xxxxx` |
| `NAVHUB_MAIL_USER` | 用于抓取验证码的 QQ 邮箱账号 | `your@qq.com` |
| `NAVHUB_MAIL_CODE` | QQ 邮箱 IMAP 授权码 | `your-imap-auth-code` |
| `NAVHUB_MAIL_INTERVAL` | 验证码轮询间隔（秒） | `15` |
| `NAVHUB_SEARCH_URL` | 全网搜索代理地址（可选） | `https://your-search-api/search` |
| `NAVHUB_SEARCH_KEY` | 搜索代理 Key（可选） | `your-search-key` |
| `NAVHUB_WEATHER_LAT/LON/CITY` | 天气城市坐标 | 香港 `22.3193` / `114.1694` |

> 不配置 `NAVHUB_AI_API_KEY` 时，AI 分类和 AI 聊天会自动降级为纯本地模式。

### 3. 开发环境启动

```bash
cd server

NAVHUB_PASSWORD=your_admin_password \
NAVHUB_VIEWER_PASSWORD=your_viewer_password \
NAVHUB_AI_BASE_URL=https://api.deepseek.com/v1 \
NAVHUB_AI_MODEL=deepseek-v4-flash \
NAVHUB_AI_API_KEY=sk-xxxxx \
.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8001
```

浏览器打开 `http://127.0.0.1:8001`，输入管理员密码进入。

### 4. 生产部署（nginx + systemd）

```bash
# systemd 服务
cp deploy/navhub.service.example /etc/systemd/system/navhub.service
# 编辑 /etc/systemd/system/navhub.service，填入密码、API Key 等
systemctl daemon-reload && systemctl enable --now navhub

# nginx 反向代理 + HTTPS（certbot 自动签发）
cp deploy/nginx.conf.example /etc/nginx/sites-available/navhub
```

## 在哪里配置 API 和 Key

### AI 接口

生产环境在 systemd 服务文件里配置：

```bash
sudo nano /etc/systemd/system/navhub.service
```

找到下面三行，取消注释并填写：

```ini
Environment=NAVHUB_AI_BASE_URL=https://api.deepseek.com/v1
Environment=NAVHUB_AI_MODEL=deepseek-v4-flash
Environment=NAVHUB_AI_API_KEY=sk-xxxxx
```

常用的 OpenAI 兼容接口示例：

| 服务商 | `NAVHUB_AI_BASE_URL` | `NAVHUB_AI_MODEL` |
|---|---|---|
| DeepSeek 官方 | `https://api.deepseek.com/v1` | `deepseek-v4-flash` / `deepseek-v4-pro` |
| 魔芋 AI 中转 | `https://www.moyu.info/v1` | `deepseek-v4-flash` / `deepseek-v4-pro` |
| OpenAI | `https://api.openai.com/v1` | `gpt-4o-mini` |

改完后：

```bash
sudo systemctl daemon-reload
sudo systemctl restart navhub
```

### 邮箱验证码 / 搜索

同样在 `deploy/navhub.service.example` 或 systemd 服务文件里添加：

```ini
Environment=NAVHUB_MAIL_USER=your@qq.com
Environment=NAVHUB_MAIL_CODE=your-imap-auth-code
Environment=NAVHUB_MAIL_INTERVAL=15

Environment=NAVHUB_SEARCH_URL=https://your-search-api/search
Environment=NAVHUB_SEARCH_KEY=your-search-key
```

QQ 邮箱需要在邮箱设置里开启 IMAP 服务，并生成“授权码”，不是 QQ 密码。

## 在哪里添加网站 / 接入游戏

NavHub 的“游戏”和普通网站一样，都是**分类 + 网站**。

### 方式一：后台界面添加（推荐）

1. 用管理员密码登录。
2. 左侧点击「新建分类」，名称填 `游戏`，图标可以填 `gamepad` 或 `🎮`。
3. 在「AI 添加网站」或「手动添加」里：
   - URL 填游戏网站地址，例如 `https://www.gamer520.com/`
   - 标题、描述、标签按需填写
   - 分类选择 `游戏`
4. 保存后就会出现在导航首页的游戏分类里。

如果想让看板娘聊天时能推荐这些游戏网站，只需要保证它们已经在收藏列表里即可，AI 会自动把收藏作为上下文。

### 方式二：导入书签 / 数据

- 在「设置 → 导入」里可以直接导入浏览器导出的书签 HTML，自动识别分类和网站。
- 也可以导入 NavHub JSON 备份。

### 方式三：直接操作数据库（高级）

数据保存在 SQLite 文件 `server/navhub.db`：

- 分类表：`categories`（id、name、icon、sort_order）
- 网站表：`sites`（category_id、title、url、description、favicon、tags）

例如插入一个游戏分类：

```sql
INSERT INTO categories (name, icon, sort_order) VALUES ('游戏', 'gamepad', 0);
```

再插入一个游戏网站：

```sql
INSERT INTO sites (category_id, title, url, description, tags)
VALUES (1, 'Gamer520', 'https://www.gamer520.com/', 'Switch/PC 游戏下载', '游戏,下载');
```

> 正常使用不需要手动操作数据库，后台界面就够了。

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
│   ├── db.py        # SQLite 数据层（分类/网站/便签/验证码）
│   ├── ai.py        # AI 分类 + 聊天
│   ├── fetch.py     # 页面信息抓取 + favicon 兜底
│   ├── mail.py      # QQ 邮箱 IMAP 验证码抓取
│   ├── checker.py   # 死链检测
│   └── sysinfo.py   # 系统监控采集
├── web/             # Vue 3 前端
│   └── src/
│       ├── App.vue  # 主界面（滑动分屏导航）
│       └── components/
│           ├── Live2dAssistant.vue  # 看板娘（聊天/AI分类/天气）
│           ├── MonitorView.vue      # 服务器监控
│           └── ParticleBg.vue       # 登录页粒子背景
└── deploy/          # systemd/nginx 部署示例
```

## License

MIT
