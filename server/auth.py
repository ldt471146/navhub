"""双角色认证：管理员密码 + 访客只读密码，session 持久化（存 SQLite，重启不失效）。"""
import hashlib
import hmac
import secrets
import sqlite3
import time
from pathlib import Path

SESSION_TTL = 60 * 60 * 24 * 90  # 90 天

PASSWORD = __import__("os").environ.get("NAVHUB_PASSWORD", "admin123456")
VIEWER_PASSWORD = __import__("os").environ.get("NAVHUB_VIEWER_PASSWORD", "viewer123456")

DB_PATH = Path(__file__).parent / "navhub.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expire_at REAL, role TEXT DEFAULT 'admin')"
    )
    # 迁移：老库补 role 列
    cols = [r[1] for r in conn.execute("PRAGMA table_info(sessions)").fetchall()]
    if "role" not in cols:
        conn.execute("ALTER TABLE sessions ADD COLUMN role TEXT DEFAULT 'admin'")
        conn.commit()
    return conn


def _hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def verify_password(pw: str) -> str | None:
    """返回角色：admin / viewer；都不匹配返回 None。"""
    if hmac.compare_digest(_hash_password(pw), _hash_password(PASSWORD)):
        return "admin"
    if hmac.compare_digest(_hash_password(pw), _hash_password(VIEWER_PASSWORD)):
        return "viewer"
    return None


def create_session(role: str = "admin") -> str:
    token = secrets.token_urlsafe(32)
    expire = time.time() + SESSION_TTL
    conn = _conn()
    conn.execute(
        "INSERT INTO sessions (token, expire_at, role) VALUES (?, ?, ?)",
        (token, expire, role),
    )
    conn.commit()
    conn.close()
    return token


def check_session(token: str | None) -> str | None:
    """返回 session 角色（admin/viewer）；无效返回 None。"""
    if not token:
        return None
    conn = _conn()
    row = conn.execute(
        "SELECT expire_at, role FROM sessions WHERE token = ?", (token,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    expire, role = row[0], row[1]
    if time.time() > expire:
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    conn.close()
    return role or "admin"


def revoke_session(token: str) -> None:
    conn = _conn()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()
