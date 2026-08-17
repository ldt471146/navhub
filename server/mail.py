"""QQ 邮箱 IMAP 验证码抓取模块。

用 imaplib 直连 imap.qq.com，拉取收件箱最新邮件，解析主题/发件人/正文，
正则提取验证码，写入 db.mail_codes（去重由 db.add_mail_code 保证）。
后台由 main.py 启动轮询线程，也可被 /api/mail/codes/poll 手动触发。
"""
import email
import imaplib
import logging
import re
import threading
import time
from email.header import decode_header

import db

log = logging.getLogger("navhub.mail")

IMAP_HOST = "imap.qq.com"
IMAP_PORT = 993

# 验证码匹配：优先"验证码/CODE/OTP/动态码"等关键词后跟 4-8 位数字/字母
_CODE_PATTERNS = [
    re.compile(r"(?:验证码|校验码|动态码|验证代码|code|otp|verification\s*code)[^0-9a-zA-Z]{0,30}([A-Za-z0-9]{4,8})", re.I),
    re.compile(r"([A-Za-z0-9]{4,8})(?:\s*(?:是|为|:))?(?:您|你的)?(?:的)?(?:验证码|校验码)", re.I),
    re.compile(r"\b([0-9]{6})\b"),  # 兜底：6 位字母数字
]

_IGNORE_SENDERS = ("no-reply@qq.com", "system@qq.com", "bounce@qq.com")


def _decode(s) -> str:
    """解码邮件头（MIME 编码）。"""
    if not s:
        return ""
    parts = decode_header(s)
    out = []
    for text, enc in parts:
        if isinstance(text, bytes):
            try:
                out.append(text.decode(enc or "utf-8", errors="replace"))
            except Exception:
                out.append(text.decode("utf-8", errors="replace"))
        else:
            out.append(text)
    return "".join(out)


def _body_text(msg) -> str:
    """提取邮件正文纯文本。"""
    if msg.is_multipart():
        for part in msg.walk():
            ct = (part.get_content_type() or "").lower()
            if ct == "text/plain":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                except Exception:
                    pass
        # 兜底：html 转纯文本
        for part in msg.walk():
            ct = (part.get_content_type() or "").lower()
            if ct == "text/html":
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        import html as _html

                        text = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                        text = re.sub(r"<[^>]+>", " ", text)
                        return _html.unescape(re.sub(r"\s+", " ", text))
                except Exception:
                    pass
        return ""
    try:
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
            # 如果是 HTML 但非 multipart，也剥离标签
            ct = (msg.get_content_type() or "").lower()
            if "html" in ct:
                text = re.sub(r"<[^>]+>", " ", text)
                import html as _html
                text = _html.unescape(re.sub(r"\s+", " ", text))
            return text
    except Exception:
        pass
    return ""


def _extract_code(subject: str, body: str) -> str | None:
    """从主题+正文提取验证码。"""
    haystack = f"{subject}\n{body}"
    for pat in _CODE_PATTERNS:
        m = pat.search(haystack)
        if m:
            code = m.group(1)
            # 排除明显不是验证码的（如年份、QQ号等过长的连续数字已由长度限制过滤）
            if 4 <= len(code) <= 8:
                return code
    return None


class MailFetcher:
    """IMAP 连接器 + 轮询。"""

    def __init__(self, user: str, auth_code: str, interval: float = 15.0):
        self.user = user
        self.auth_code = auth_code
        self.interval = max(5.0, float(interval))
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None

    def fetch_once(self, limit: int = 10) -> list[dict]:
        """拉取一次：只处理最新一封含验证码的邮件（从新到旧扫描，找到即停）。"""
        added = []
        try:
            conn = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT, timeout=30)
            try:
                conn.login(self.user, self.auth_code)
                conn.select("INBOX")
                # 最近 limit 封（按 UID 倒序取）
                typ, data = conn.search(None, "ALL")
                if typ != "OK" or not data or not data[0]:
                    return added
                uids = data[0].split()
                recent = uids[-limit:]
                # 从最新到最旧扫描，只取最新一封验证码邮件
                for uid in reversed(recent):
                    typ, msg_data = conn.fetch(uid, "(BODY.PEEK[] RFC822.HEADER)")
                    if typ != "OK" or not msg_data:
                        continue
                    raw = msg_data[0][1] if isinstance(msg_data[0], tuple) else None
                    if not raw:
                        continue
                    msg = email.message_from_bytes(raw)
                    subject = _decode(msg.get("Subject", ""))
                    sender_raw = _decode(msg.get("From", ""))
                    date_raw = _decode(msg.get("Date", ""))
                    body = _body_text(msg)
                    sender = sender_raw.split("<")[-1].rstrip(">").strip() if "<" in sender_raw else sender_raw.strip()
                    code = _extract_code(subject, body)
                    if code:
                        ok = db.add_mail_code(sender[:80], subject[:120], code, date_raw[:40])
                        if ok:
                            added.append({"sender": sender, "subject": subject, "code": code})
                        break  # 只处理最新一封，历史验证码不重复入库
            finally:
                try:
                    conn.logout()
                except Exception:
                    pass
        except Exception as e:
            log.warning("IMAP fetch failed: %s", e)
        return added

    def _loop(self):
        while not self._stop.is_set():
            try:
                self.fetch_once()
            except Exception as e:
                log.warning("IMAP loop error: %s", e)
            self._stop.wait(self.interval)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True, name="navhub-mail-imap")
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)
