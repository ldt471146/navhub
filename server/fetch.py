"""页面抓取：标题 / 描述 / favicon。超时、降级，不落库。"""
import re
from urllib.parse import urlparse

import httpx

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
TIMEOUT = 8.0
MAX_BYTES = 512 * 1024


def _normalize_url(url: str) -> str:
    url = url.strip()
    if not url:
        raise ValueError("URL 不能为空")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    parsed = urlparse(url)
    if not parsed.netloc:
        raise ValueError("URL 格式不正确")
    return url


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    return ""


def _extract_meta(html: str, names: tuple) -> str:
    for name in names:
        m = re.search(
            rf'<meta[^>]+(?:name|property)=["\']{re.escape(name)}["\'][^>]*content=["\'](.*?)["\']',
            html, re.I | re.S,
        )
        if not m:
            m = re.search(
                rf'<meta[^>]+content=["\'](.*?)["\'][^>]*(?:name|property)=["\']{re.escape(name)}["\']',
                html, re.I | re.S,
            )
        if m:
            val = re.sub(r"\s+", " ", m.group(1)).strip()[:300]
            if val:
                return val
    return ""


def _extract_favicon(html: str, base_url: str) -> str:
    m = re.search(
        r'<link[^>]+rel=["\'](?:shortcut )?icon["\'][^>]+href=["\'](.*?)["\']',
        html, re.I,
    )
    if not m:
        m = re.search(
            r'<link[^>]+href=["\'](.*?)["\'][^>]+rel=["\'](?:shortcut )?icon["\']',
            html, re.I,
        )
    if m:
        href = m.group(1).strip()
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}{href}"
        elif not href.startswith("http"):
            href = f"{base_url.rstrip('/')}/{href}"
        return href
    # 降级：页面没声明图标，用公共图标服务（站点自身 /favicon.ico 经常 404）
    return duckduckgo_icon(urlparse(base_url).netloc)


def duckduckgo_icon(host: str) -> str:
    """DuckDuckGo 公共图标服务，覆盖绝大多数网站，无需 key。"""
    return f"https://icons.duckduckgo.com/ip3/{host}.ico"


def fetch_page(url: str) -> dict:
    """抓取页面元信息。失败时返回降级结果，不抛异常。"""
    try:
        url = _normalize_url(url)
    except ValueError as e:
        return {"url": url, "title": "", "description": "", "favicon": "", "error": str(e)}

    try:
        resp = httpx.get(
            url,
            headers={"User-Agent": UA, "Accept-Language": "zh-CN,zh;q=0.9"},
            timeout=TIMEOUT,
            follow_redirects=True,
        )
        resp.raise_for_status()
        ctype = resp.headers.get("content-type", "")
        if "text" not in ctype and "html" not in ctype and "xml" not in ctype:
            # 非 HTML（图片/文件），没有可抓内容
            host = urlparse(url).netloc
            return {
                "url": url,
                "title": host,
                "description": "",
                "favicon": duckduckgo_icon(host),
                "error": "",
            }
        html = resp.content[:MAX_BYTES].decode("utf-8", errors="ignore")
        final_url = str(resp.url)
        return {
            "url": final_url,
            "title": _extract_title(html) or urlparse(final_url).netloc,
            "description": _extract_meta(html, ("description", "og:description")),
            "favicon": _extract_favicon(html, final_url),
            "error": "",
        }
    except Exception as e:
        host = urlparse(url).netloc
        return {
            "url": url,
            "title": host or url,
            "description": "",  # 抓取失败不写错误文案，AI 添加时会由 AI 生成描述
            "favicon": duckduckgo_icon(host),
            "error": str(e),  # 仅供调试，前端不展示
        }
