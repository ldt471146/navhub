"""网站死链检测：并发 HEAD/GET 探测可达性，更新 sites.status。"""
import asyncio
import logging

import httpx

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"

log = logging.getLogger("navhub.checker")


async def _check_one(client: httpx.AsyncClient, site: dict) -> str:
    """返回 'ok' / 'down'。"""
    url = (site.get("url") or "").strip()
    if not url.startswith(("http://", "https://")):
        return "ok"  # 非 http 链接不探测，视为正常
    try:
        resp = await client.head(url, follow_redirects=True, timeout=6.0)
        # 部分站点 HEAD 被拒（405/403），降级 GET
        if resp.status_code in (405, 403, 501):
            resp = await client.get(url, follow_redirects=True, timeout=6.0)
        return "ok" if resp.status_code < 500 else "down"
    except Exception:
        return "down"


async def run_check(sites: list[dict], concurrency: int = 10) -> dict:
    """并发探测一批网站，返回 {site_id: status}。"""
    limits = httpx.Limits(max_connections=concurrency, max_keepalive_connections=concurrency)
    async with httpx.AsyncClient(
        headers={"User-Agent": UA, "Accept": "*/*"},
        limits=limits,
        trust_env=False,
    ) as client:
        results = {}
        sem = asyncio.Semaphore(concurrency)

        async def wrapped(site: dict):
            async with sem:
                results[site["id"]] = await _check_one(client, site)

        await asyncio.gather(*(wrapped(s) for s in sites))
    return results


def check_sites(sites: list[dict]) -> dict:
    """同步入口（uvicorn 线程池调用）。"""
    try:
        return asyncio.run(run_check(sites))
    except Exception as e:
        log.warning("死链检测失败: %s", e)
        return {}
