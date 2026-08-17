"""NavHub API 入口。"""
import json
import os
import threading
import time
from pathlib import Path

import httpx

from fastapi import Cookie, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import ai
import auth
import checker
import db
import fetch
import mail as mailmod
import sysinfo

app = FastAPI(title="NavHub", docs_url=None, redoc_url=None)

# 允许插件和前端跨域（简单场景用；生产同域可收紧）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

WEB_DIST = Path(__file__).parent.parent / "web" / "dist"


# ---------- 模型 ----------

class LoginIn(BaseModel):
    password: str


class CategoryIn(BaseModel):
    name: str
    icon: str = ""


class CategoryPatch(BaseModel):
    name: str | None = None
    icon: str | None = None
    sort_order: int | None = None


class SiteIn(BaseModel):
    category_id: int | None = None
    title: str = ""
    url: str
    description: str = ""
    favicon: str = ""
    tags: str = ""


class SitePatch(BaseModel):
    category_id: int | None = None
    title: str | None = None
    url: str | None = None
    description: str | None = None
    favicon: str | None = None
    tags: str | None = None
    sort_order: int | None = None
    pinned: bool | None = None


class TagRenameIn(BaseModel):
    old: str
    new: str = ""  # 空字符串 = 从所有站点移除该标签


class BulkMoveIn(BaseModel):
    site_ids: list[int]
    category_id: int | None = None


class MailCodeIn(BaseModel):
    sender: str = ""
    subject: str = ""
    code: str
    mail_time: str = ""


class SearchIn(BaseModel):
    query: str
    max_results: int = 5
    include_answer: bool = True


class ClassifyIn(BaseModel):
    url: str


class SaveIn(BaseModel):
    url: str
    title: str = ""
    category_id: int | None = None
    new_category: str | None = None
    description: str = ""
    favicon: str = ""
    tags: str = ""


# ---------- 认证 ----------

def require_auth(session: str | None) -> str:
    """校验登录，返回角色 admin/viewer。未登录抛 401。"""
    role = auth.check_session(session)
    if not role:
        raise HTTPException(status_code=401, detail="未登录")
    return role


def require_admin(session: str | None) -> None:
    """访客只读：写操作必须管理员。"""
    role = require_auth(session)
    if role != "admin":
        raise HTTPException(status_code=403, detail="访客模式，仅可查看")


@app.post("/api/auth/login")
def login(body: LoginIn, request: Request, response: JSONResponse):
    ip = _client_ip(request)
    locked, remain = auth.login_locked(ip)
    if locked:
        raise HTTPException(
            status_code=429,
            detail=f"尝试过于频繁，请 {int(remain // 60) + 1} 分钟后重试",
        )
    role = auth.verify_password(body.password)
    if not role:
        auth.record_login_fail(ip)
        raise HTTPException(status_code=401, detail="密码错误")
    auth.record_login_ok(ip)
    auth.cleanup_sessions()
    token = auth.create_session(role)
    resp = JSONResponse({"ok": True, "role": role})
    resp.set_cookie("session", token, httponly=True, samesite="lax", max_age=86400 * 90, path="/")
    return resp


def _client_ip(request: Request) -> str:
    """经 nginx 反代取真实客户端 IP（信任 X-Forwarded-For，8001 仅本机监听）。"""
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@app.get("/api/auth/me")
def me(session: str | None = Cookie(default=None)):
    role = auth.check_session(session)
    if not role:
        return {"ok": False}
    return {"ok": True, "role": role}


@app.post("/api/auth/logout")
def logout(response: JSONResponse):
    resp = JSONResponse({"ok": True})
    resp.delete_cookie("session", path="/")
    return resp


# ---------- 分类 ----------

@app.get("/api/categories")
def list_categories(session: str | None = Cookie(default=None)):
    require_auth(session)
    return db.list_categories()


@app.post("/api/categories")
def create_category(body: CategoryIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="分类名不能为空")
    try:
        return db.create_category(body.name, body.icon)
    except Exception:
        raise HTTPException(status_code=400, detail="分类已存在")


@app.patch("/api/categories/{cid}")
def update_category(cid: int, body: CategoryPatch, session: str | None = Cookie(default=None)):
    require_admin(session)
    if not db.get_category(cid):
        raise HTTPException(status_code=404, detail="分类不存在")
    db.update_category(cid, body.name, body.icon, body.sort_order)
    return db.get_category(cid)


@app.delete("/api/categories/{cid}")
def delete_category(cid: int, session: str | None = Cookie(default=None)):
    require_admin(session)
    if not db.get_category(cid):
        raise HTTPException(status_code=404, detail="分类不存在")
    db.delete_category(cid)
    return {"ok": True}


# ---------- 网站 ----------

@app.get("/api/sites")
def list_sites(category_id: int | None = None, tag: str | None = None, session: str | None = Cookie(default=None)):
    require_auth(session)
    sites = db.list_sites(category_id, tag)
    # 性能防线：过滤 base64/超长 favicon（曾导致 API 700KB+）
    for s in sites:
        fav = s.get("favicon") or ""
        if "base64" in fav or len(fav) > 500:
            s["favicon"] = ""
    return sites


@app.post("/api/sites")
def create_site(body: SiteIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    fav = (body.favicon or "").strip()
    if "base64" in fav or len(fav) > 500:
        fav = ""
    title = body.title or fetch.fetch_page(body.url)["title"]
    try:
        return db.create_site(body.category_id, title, body.url, body.description, fav, body.tags)
    except Exception:
        raise HTTPException(status_code=400, detail="URL 已存在")


@app.patch("/api/sites/{sid}")
def update_site(sid: int, body: SitePatch, session: str | None = Cookie(default=None)):
    require_admin(session)
    fav = (body.favicon or "").strip() if body.favicon is not None else None
    if fav and ("base64" in fav or len(fav) > 500):
        fav = ""
    if not db.get_site(sid):
        raise HTTPException(status_code=404, detail="网站不存在")
    try:
        db.update_site(
            sid,
            category_id=body.category_id,
            title=body.title,
            url=body.url,
            description=body.description,
            favicon=fav,
            tags=body.tags,
            sort_order=body.sort_order,
            pinned=body.pinned,
        )
    except Exception:
        raise HTTPException(status_code=400, detail="URL 已存在，请换一个")
    return db.get_site(sid)


@app.delete("/api/sites/{sid}")
def delete_site(sid: int, session: str | None = Cookie(default=None)):
    require_admin(session)
    db.delete_site(sid)
    return {"ok": True}


# ---------- 批量操作（第二轮升级） ----------

@app.post("/api/sites/move-bulk")
def move_sites_bulk(body: BulkMoveIn, session: str | None = Cookie(default=None)):
    """批量移动分类：单次更新多个站点。"""
    require_admin(session)
    if not body.site_ids:
        raise HTTPException(status_code=400, detail="site_ids 不能为空")
    for sid in body.site_ids:
        db.update_site(sid, category_id=body.category_id)
    return {"ok": True, "moved": len(body.site_ids)}


@app.post("/api/tags/rename")
def rename_tag(body: TagRenameIn, session: str | None = Cookie(default=None)):
    """标签重命名（new 为空 = 移除）：遍历所有站点更新 tags。"""
    require_admin(session)
    old = body.old.strip()
    if not old:
        raise HTTPException(status_code=400, detail="标签不能为空")
    new = body.new.strip()
    sites = db.list_sites()
    affected = 0
    for s in sites:
        tags = [t.strip() for t in (s.get("tags") or "").split(",") if t.strip()]
        if old in tags:
            if new:
                tags = [new if t == old else t for t in tags]
            else:
                tags = [t for t in tags if t != old]
            db.update_site(s["id"], tags=",".join(tags))
            affected += 1
    return {"ok": True, "affected": affected}


# ---------- 邮箱验证码速取（第三轮） ----------

MAIL_INGEST_KEY = os.environ.get("NAVHUB_MAIL_INGEST_KEY", "navhub-mail-ingest-2026")

# 全网搜索代理（Tavily Hikari，key 只存服务器）
SEARCH_URL = os.environ.get("NAVHUB_SEARCH_URL", "https://search.diecast.cloud/api/tavily/search")
SEARCH_KEY = os.environ.get("NAVHUB_SEARCH_KEY", "")

# IMAP 直连（第三轮升级：服务器端直接拉取 QQ 邮箱，无需本机脚本）
MAIL_USER = os.environ.get("NAVHUB_MAIL_USER", "")
MAIL_CODE = os.environ.get("NAVHUB_MAIL_CODE", "")
MAIL_INTERVAL = float(os.environ.get("NAVHUB_MAIL_INTERVAL", "15"))

_mail_fetcher = None
if MAIL_USER and MAIL_CODE:
    try:
        _mail_fetcher = mailmod.MailFetcher(MAIL_USER, MAIL_CODE, MAIL_INTERVAL)
        _mail_fetcher.start()
    except Exception as e:
        print(f"[navhub] IMAP fetcher init failed: {e}", flush=True)


@app.post("/api/mail/codes/ingest")
def mail_codes_ingest(body: MailCodeIn, key: str = Query(default="")):
    """本机抓取脚本上报验证码（密钥保护）。"""
    if key != MAIL_INGEST_KEY:
        raise HTTPException(status_code=403, detail="key 错误")
    code = body.code.strip()
    if not code:
        raise HTTPException(status_code=400, detail="code 不能为空")
    added = db.add_mail_code(
        body.sender.strip(), body.subject.strip(), code, body.mail_time.strip()
    )
    return {"ok": True, "added": added}


@app.get("/api/mail/codes")
def mail_codes_list(session: str | None = Cookie(default=None)):
    require_auth(session)
    db.cleanup_mail_codes()  # 惰性清理过期验证码
    return db.list_mail_codes(20)


@app.post("/api/mail/codes/poll")
def mail_codes_poll(session: str | None = Cookie(default=None)):
    """手动触发一次即时拉取（前端「立即刷新」按钮）。"""
    require_auth(session)
    added = []
    if _mail_fetcher:
        added = _mail_fetcher.fetch_once()
    db.cleanup_mail_codes()
    return {"ok": True, "added": len(added), "enabled": _mail_fetcher is not None}


@app.get("/api/mail/codes/unread")
def mail_codes_unread(session: str | None = Cookie(default=None)):
    require_auth(session)
    return db.unread_mail_codes()


@app.post("/api/mail/codes/mark-read")
def mail_codes_mark_read(session: str | None = Cookie(default=None)):
    require_admin(session)
    db.mark_mail_codes_read()
    return {"ok": True}


@app.delete("/api/mail/codes/{cid}")
def mail_codes_delete(cid: int, session: str | None = Cookie(default=None)):
    require_admin(session)
    db.delete_mail_code(cid)
    return {"ok": True}


# ---------- 全网搜索代理（Tavily Hikari） ----------

@app.post("/api/search")
def search_web(body: SearchIn, session: str | None = Cookie(default=None)):
    """代理搜索请求：key 只存服务器，前端不暴露。"""
    require_auth(session)
    q = body.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="query 不能为空")
    if len(q) > 200:
        raise HTTPException(status_code=400, detail="query 过长")
    if not SEARCH_KEY:
        raise HTTPException(status_code=503, detail="搜索引擎未配置")
    try:
        resp = httpx.post(
            SEARCH_URL,
            json={
                "query": q,
                "max_results": min(body.max_results, 8),
                "include_answer": body.include_answer,
            },
            headers={"Authorization": f"Bearer {SEARCH_KEY}"},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"搜索服务错误 {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"搜索失败: {e}")


class NoteIn(BaseModel):
    content: str


class NoteReorderIn(BaseModel):
    order: list[int]


class ChatIn(BaseModel):
    message: str
    history: list[dict] = []


# ---------- 便签 ----------

@app.get("/api/notes")
def list_notes(session: str | None = Cookie(default=None)):
    require_auth(session)
    return db.list_notes()


@app.post("/api/notes/reorder")
def reorder_notes(body: NoteReorderIn, session: str | None = Cookie(default=None)):
    require_auth(session)
    db.reorder_notes(body.order)
    return {"ok": True}


@app.post("/api/notes")
def create_note(body: NoteIn, session: str | None = Cookie(default=None)):
    require_auth(session)
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    return db.create_note(body.content)


# ---------- 机器人聊天（AI，基于导航推荐） ----------

@app.post("/api/chat")
def chat(body: ChatIn, session: str | None = Cookie(default=None)):
    require_auth(session)
    if not body.message.strip():
        raise HTTPException(status_code=400, detail="消息不能为空")
    # 组装网站列表（带分类名），供 AI 基于收藏推荐
    sites = db.list_sites()
    cats = {c["id"]: c["name"] for c in db.list_categories()}
    for s in sites:
        s["category_name"] = cats.get(s.get("category_id"))
    reply = ai.chat(body.message.strip()[:500], body.history or [], sites)
    return reply


@app.patch("/api/notes/{nid}")
def update_note(nid: int, body: NoteIn, session: str | None = Cookie(default=None)):
    require_auth(session)
    if not db.get_note(nid):
        raise HTTPException(status_code=404, detail="便签不存在")
    if not body.content.strip():
        raise HTTPException(status_code=400, detail="内容不能为空")
    db.update_note(nid, body.content)
    return db.get_note(nid)


@app.delete("/api/notes/{nid}")
def delete_note(nid: int, session: str | None = Cookie(default=None)):
    require_auth(session)
    db.delete_note(nid)
    return {"ok": True}


# ---------- 页面信息抓取（不调 AI，手动添加时自动填充） ----------

class FetchIn(BaseModel):
    url: str


@app.post("/api/sites/fetch-meta")
def fetch_meta(body: FetchIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    return fetch.fetch_page(body.url)


# ---------- AI 分类 ----------

@app.post("/api/sites/ai-classify")
def ai_classify(body: ClassifyIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    page = fetch.fetch_page(body.url)
    categories = db.list_categories()
    # 给分类带上站点示例
    for c in categories:
        c["sites"] = db.list_sites(c["id"])[:5]
    result = ai.classify_url(page["url"], page["title"], page["description"], categories)
    return {"page": page, "suggestion": result}


@app.post("/api/sites/ai-save")
def ai_save(body: SaveIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    category_id = body.category_id
    if body.new_category:
        category_id = db.create_category(body.new_category)["id"]
    title = body.title or fetch.fetch_page(body.url)["title"]
    try:
        return db.create_site(category_id, title, body.url, body.description, body.favicon, body.tags)
    except Exception:
        raise HTTPException(status_code=400, detail="URL 已存在")


# ---------- 系统监控 ----------

@app.get("/api/system/stats")
def system_stats(session: str | None = Cookie(default=None)):
    require_auth(session)
    return sysinfo.get_system_stats()


# ---------- 天气（open-meteo 免费代理，无需 key；带 10 分钟缓存） ----------

import time as _time

_weather_cache = {"t": 0, "data": None}
WEATHER_LAT = float(os.environ.get("NAVHUB_WEATHER_LAT", "22.3193"))   # 默认香港
WEATHER_LON = float(os.environ.get("NAVHUB_WEATHER_LON", "114.1694"))
WEATHER_CITY = os.environ.get("NAVHUB_WEATHER_CITY", "香港")
_WCODE = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴",
    45: "雾", 48: "雾凇", 51: "毛毛雨", 53: "小毛毛雨", 55: "大毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "阵雨", 81: "强阵雨", 82: "暴雨", 85: "阵雪", 86: "强阵雪",
    95: "雷暴", 96: "雷暴伴冰雹", 99: "强雷暴伴冰雹",
}


@app.get("/api/weather")
def weather(session: str | None = Cookie(default=None)):
    require_auth(session)
    now = _time.time()
    if _weather_cache["data"] and now - _weather_cache["t"] < 600:
        return _weather_cache["data"]
    try:
        import urllib.request
        url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={WEATHER_LAT}&longitude={WEATHER_LON}"
            "&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m"
            "&timezone=Asia%2FShanghai"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 navhub"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode())
        cur = data.get("current", {})
        result = {
            "city": WEATHER_CITY,
            "temp": cur.get("temperature_2m"),
            "humidity": cur.get("relative_humidity_2m"),
            "wind": cur.get("wind_speed_10m"),
            "code": cur.get("weather_code"),
            "desc": _WCODE.get(cur.get("weather_code"), "未知"),
            "time": cur.get("time", ""),
        }
        _weather_cache["t"] = now
        _weather_cache["data"] = result
        return result
    except Exception:
        return {"city": WEATHER_CITY, "error": "天气服务暂不可用"}


# ---------- 设置（背景等 UI 偏好） ----------

class SettingIn(BaseModel):
    key: str
    value: str


@app.get("/api/settings")
def get_settings(session: str | None = Cookie(default=None)):
    require_auth(session)
    return db.all_settings()


@app.post("/api/settings")
def set_setting(body: SettingIn, session: str | None = Cookie(default=None)):
    require_admin(session)
    db.set_setting(body.key, body.value)
    return {"ok": True}


# ---------- 导出 / 导入（备份与恢复） ----------

@app.get("/api/export")
def export_data(session: str | None = Cookie(default=None)):
    require_auth(session)
    cats = db.list_categories()
    sites = db.list_sites()
    notes = db.list_notes()
    return {
        "app": "navhub",
        "version": 1,
        "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "categories": [{k: c[k] for k in ("id", "name", "icon", "sort_order")} for c in cats],
        "sites": [{k: s[k] for k in ("id", "category_id", "title", "url", "description", "favicon", "tags", "pinned", "sort_order")} for s in sites],
        "notes": [{k: n[k] for k in ("id", "content", "sort_order")} for n in notes],
    }


@app.post("/api/import")
def import_data(body: dict, session: str | None = Cookie(default=None)):
    require_admin(session)
    # 兼容两种格式：{"data": {...}} 包装，或直接传导出结构
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    data = data or {}
    # 模式：合并导入（不覆盖已有）
    result = {"categories": 0, "sites": 0, "notes": 0}

    # 1) 分类（同名跳过）
    cat_map = {}  # 旧 id -> 新 id
    for c in data.get("categories", []):
        name = (c.get("name") or "").strip()
        if not name:
            continue
        exist = [x for x in db.list_categories() if x["name"] == name]
        if exist:
            cat_map[c.get("id")] = exist[0]["id"]
        else:
            new_c = db.create_category(name, c.get("icon", ""))
            cat_map[c.get("id")] = new_c["id"]
            result["categories"] += 1

    # 2) 网站（URL 重复跳过）
    for s in data.get("sites", []):
        url = (s.get("url") or "").strip()
        if not url:
            continue
        try:
            db.create_site(
                cat_map.get(s.get("category_id")),
                s.get("title") or url,
                url,
                s.get("description", ""),
                s.get("favicon", ""),
                s.get("tags", ""),
            )
            result["sites"] += 1
        except Exception:
            continue  # URL 已存在

    # 3) 便签（按内容去重）
    exist_contents = {n["content"].strip() for n in db.list_notes()}
    for n in data.get("notes", []):
        content = (n.get("content") or "").strip()
        if content and content not in exist_contents:
            db.create_note(content)
            exist_contents.add(content)
            result["notes"] += 1

    return result


# ---------- 死链检测 ----------

_HEALTH_LOCK = threading.Lock()

def _run_health_check() -> dict:
    """执行一轮全站探测并落库，返回统计。"""
    sites = db.list_sites()
    results = checker.check_sites(sites)
    ok = down = 0
    for s in sites:
        st = results.get(s["id"])
        if st is None:
            continue
        if st == "ok":
            ok += 1
        else:
            down += 1
        db.set_site_status(s["id"], st)
    return {"total": len(sites), "checked": len(results), "ok": ok, "down": down}


@app.post("/api/health-check")
def health_check(session: str | None = Cookie(default=None)):
    require_admin(session)
    if _HEALTH_LOCK.locked():
        raise HTTPException(status_code=409, detail="检测正在进行中，请稍候")
    with _HEALTH_LOCK:
        return _run_health_check()


def _background_health_loop(interval_hours: float = 6.0):
    """后台定时探测（每 6 小时一轮）。"""
    while True:
        time.sleep(interval_hours * 3600)
        try:
            _run_health_check()
        except Exception as e:
            print(f"[navhub] 定时死链检测失败: {e}", flush=True)


# ---------- 点击统计 ----------

class ClickIn(BaseModel):
    site_id: int


@app.post("/api/sites/click")
def click_site(body: ClickIn, session: str | None = Cookie(default=None)):
    require_auth(session)
    db.increment_clicks(body.site_id)
    return {"ok": True}


@app.get("/api/sites/top")
def top_sites(session: str | None = Cookie(default=None)):
    require_auth(session)
    return db.top_sites(8)


# ---------- 前端静态文件 ----------

@app.get("/")
def index():
    if WEB_DIST.exists():
        return FileResponse(WEB_DIST / "index.html")
    return {"message": "NavHub API running. 前端未构建。"}


if WEB_DIST.exists():
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")


@app.get("/{filename}")
def static_file(filename: str):
    """PWA 等静态文件（manifest/sw/icon），不在 /assets 下的。"""
    if not WEB_DIST.exists():
        raise HTTPException(status_code=404)
    # 防目录穿越
    safe = Path(filename).name
    if safe != filename:
        raise HTTPException(status_code=404)
    f = WEB_DIST / safe
    if f.is_file() and safe in (
        "manifest.webmanifest", "sw.js",
        "icon-192.png", "icon-512.png", "apple-touch-icon.png",
        "favicon.svg", "icons.svg", "icon.svg",
    ):
        return FileResponse(f)
    raise HTTPException(status_code=404)


if __name__ == "__main__":
    import uvicorn

    threading.Thread(
        target=_background_health_loop, daemon=True, name="navhub-health"
    ).start()
    uvicorn.run(app, host="127.0.0.1", port=int(os.environ.get("NAVHUB_PORT", "8001")))
