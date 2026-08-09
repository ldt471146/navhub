"""AI 自动分类：调用 DeepSeek（opencode 中转）把 URL 归入已有分类。"""
import json
import os
import re
from pathlib import Path

import httpx

# 默认复用 Hermes 的 opencode 中转配置；可用环境变量覆盖
# 默认 OpenAI 兼容端点；部署时用 NAVHUB_AI_BASE_URL / NAVHUB_AI_API_KEY 覆盖（见 deploy/navhub.service.example）
AI_BASE_URL = os.environ.get("NAVHUB_AI_BASE_URL", "https://api.openai.com/v1")
AI_MODEL = os.environ.get("NAVHUB_AI_MODEL", "deepseek-chat")
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

SYSTEM_PROMPT = """你是一个网站分类助手。用户维护一个个人网站导航，已有若干分类，每个分类下有一些示例网站。
请根据目标网站的内容，判断它最适合放进哪个已有分类，为网站写一句简单描述，并打上综合标签。

规则：
1. 只输出 JSON，格式：{"category": "分类名或null", "confidence": 0到1的小数, "reason": "一句话中文理由", "new_category": "建议新建分类名或null", "description": "一句简单中文描述，10-25字", "tags": ["标签1", "标签2"]}
2. category 必须是已有分类名之一；如果已有分类都不合适，category 设为 null，并在 new_category 给出建议名
3. confidence 表示你对这个判断的把握：>=0.7 很确定；0.4-0.7 一般；<0.4 没把握
4. reason 不超过 20 个字
5. description 用一句自然的话概括网站用途，比如「AI 对话助手」或「开源代码托管平台」，不要带标点结尾
6. tags 输出 1-3 个综合大类标签，必须从以下列表选：AI、影视、音乐、游戏、教育、新闻、工具、社交、社区、购物、娱乐、技术、设计、阅读、体育、生活、旅行、美食、金融、求职
7. 不要输出 JSON 以外的任何内容"""


def _load_api_key() -> str:
    return os.environ.get("NAVHUB_AI_API_KEY", "")


def classify_url(url: str, title: str, description: str, categories: list[dict]) -> dict:
    """调用 LLM 分类。返回 {category, confidence, reason, new_category} 或降级结果。"""
    api_key = _load_api_key()
    if not api_key:
        return {"category": None, "confidence": 0.0, "reason": "未配置 AI API key", "new_category": None, "description": "", "tags": ""}

    if not categories:
        return {"category": None, "confidence": 0.0, "reason": "还没有分类，先手动建一个", "new_category": None, "description": "", "tags": ""}

    cat_lines = []
    for c in categories:
        example = ""
        sites = c.get("sites", [])[:5]
        if sites:
            example = " 示例: " + "、".join(s["title"] for s in sites)
        cat_lines.append(f"- {c['name']}{example}")

    user_prompt = f"""已有分类：
{chr(10).join(cat_lines)}

目标网站：
- URL: {url}
- 标题: {title or '未知'}
- 描述: {description or '无'}

判断它应归入哪个分类，只输出 JSON。"""

    try:
        resp = httpx.post(
            f"{AI_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": UA,
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.2,
                "max_tokens": 300,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        result = _parse_json(content)
        # 校验 category 必须是已有分类名
        valid = {c["name"] for c in categories}
        if result.get("category") and result["category"] not in valid:
            result["category"] = None
        # 兜底：AI 没给标签时用分类名/新分类名当标签
        if not result.get("tags"):
            fallback = result.get("category") or result.get("new_category")
            if fallback:
                result["tags"] = fallback
        return result
    except Exception as e:
        return {"category": None, "confidence": 0.0, "reason": f"AI 调用失败：{type(e).__name__}", "new_category": None, "description": "", "tags": ""}


def _parse_json(content: str) -> dict:
    """解析 LLM 输出，容忍代码块包裹和多余文本。"""
    content = content.strip()
    # 去 ```json ``` 包裹
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.S)
    if m:
        content = m.group(1)
    else:
        # 找第一个 { 到最后一个 }
        s, e = content.find("{"), content.rfind("}")
        if s >= 0 and e > s:
            content = content[s : e + 1]
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {"category": None, "confidence": 0.0, "reason": "AI 返回格式异常", "new_category": None, "description": "", "tags": ""}
    raw_tags = data.get("tags") or []
    if isinstance(raw_tags, str):
        tags = ",".join(t.strip() for t in raw_tags.split(",") if t.strip())
    else:
        tags = ",".join(str(t).strip() for t in raw_tags if str(t).strip())
    return {
        "category": data.get("category") or None,
        "confidence": float(data.get("confidence", 0.0)),
        "reason": data.get("reason", "") or "",
        "new_category": data.get("new_category") or None,
        "description": data.get("description", "") or "",
        "tags": tags,
    }


# ---------- 机器人聊天（AI + 基于导航推荐） ----------

CHAT_SYSTEM_TEMPLATE = """你是 NavHub 导航站的二次元助手「小导航」，性格活泼可爱，说话简短自然，用中文回复。
用户的个人导航里收藏了这些网站（格式：分类 | 标题 | 描述 | URL | 标签）：

{site_list}

聊天规则：
1. 用户问「推荐网站/用什么网站/哪个好」这类问题时，优先从上面的收藏里推荐，给出网站标题和 URL，并简单说明理由；收藏里没有合适的话，可以推荐常识性网站并说明不在收藏里。
2. 用户问导航相关的问题（分类、标签、怎么找网站）也可以回答。
3. 其他闲聊随意发挥，但要简短（不超过 80 字），语气可爱。
4. 不要编造收藏里不存在的 URL 细节，不要输出 markdown 表格。"""


def chat(message: str, history: list[dict], sites: list[dict]) -> str:
    """AI 聊天。history: [{"role": "user"|"assistant", "content": str}, ...]（不含本次消息）"""
    api_key = _load_api_key()
    if not api_key:
        return "哎呀，AI 没配置好，暂时只能陪你唠嗑～"

    site_lines = []
    for s in sites[:120]:
        desc = (s.get("description") or "").strip()[:40]
        tags = (s.get("tags") or "").strip()
        site_lines.append(
            f"- {s.get('category_name') or '未分类'} | {s.get('title')} | {desc} | {s.get('url')} | {tags}"
        )
    if not site_lines:
        site_lines.append("（收藏还是空的）")

    system = CHAT_SYSTEM_TEMPLATE.format(site_list="\n".join(site_lines))

    messages = [{"role": "system", "content": system}]
    # 最近 8 条历史
    for h in history[-8:]:
        role = h.get("role")
        if role in ("user", "assistant") and h.get("content"):
            messages.append({"role": role, "content": h["content"][:500]})
    messages.append({"role": "user", "content": message[:500]})

    try:
        resp = httpx.post(
            f"{AI_BASE_URL.rstrip('/')}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "User-Agent": UA,
                "Content-Type": "application/json",
            },
            json={
                "model": AI_MODEL,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 400,
            },
            timeout=30.0,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return (content or "").strip() or "……我走神了，再说一遍？"
    except Exception as e:
        return f"哎呀，AI 暂时走神了（{type(e).__name__}），等会儿再找我吧～"
