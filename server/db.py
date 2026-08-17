"""SQLite 数据访问层。单用户应用，直接用 sqlite3，不引入 ORM。"""
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(__file__).parent / "navhub.db"
_lock = threading.Lock()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def init_db() -> None:
    with _lock:
        conn = get_conn()
        conn.execute("PRAGMA journal_mode = WAL")
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS categories (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL UNIQUE,
                icon       TEXT DEFAULT '',
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS sites (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER,
                title       TEXT NOT NULL,
                url         TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                favicon     TEXT DEFAULT '',
                tags        TEXT DEFAULT '',
                pinned      INTEGER DEFAULT 0,
                status      TEXT DEFAULT 'unknown',
                status_at   TEXT DEFAULT '',
                clicks      INTEGER DEFAULT 0,
                sort_order  INTEGER DEFAULT 0,
                created_at  TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS notes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                content    TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT DEFAULT (datetime('now', 'localtime'))
            );
            CREATE TABLE IF NOT EXISTS mail_codes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                sender     TEXT DEFAULT '',
                subject    TEXT DEFAULT '',
                code       TEXT NOT NULL,
                mail_time  TEXT DEFAULT '',
                fetched_at TEXT DEFAULT (datetime('now', 'localtime')),
                is_read    INTEGER DEFAULT 0
            );
            """
        )
        # 迁移：老库补 tags 列
        cols = [r[1] for r in conn.execute("PRAGMA table_info(sites)").fetchall()]
        if "tags" not in cols:
            conn.execute("ALTER TABLE sites ADD COLUMN tags TEXT DEFAULT ''")
        # 迁移：老库补 pinned 列
        if "pinned" not in cols:
            conn.execute("ALTER TABLE sites ADD COLUMN pinned INTEGER DEFAULT 0")
        # 迁移：老库补 status / status_at / clicks 列
        if "status" not in cols:
            conn.execute("ALTER TABLE sites ADD COLUMN status TEXT DEFAULT 'unknown'")
        if "status_at" not in cols:
            conn.execute("ALTER TABLE sites ADD COLUMN status_at TEXT DEFAULT ''")
        if "clicks" not in cols:
            conn.execute("ALTER TABLE sites ADD COLUMN clicks INTEGER DEFAULT 0")
        # 迁移：老库补 notes.sort_order 列
        ncols = [r[1] for r in conn.execute("PRAGMA table_info(notes)").fetchall()]
        if ncols and "sort_order" not in ncols:
            conn.execute("ALTER TABLE notes ADD COLUMN sort_order INTEGER DEFAULT 0")
        conn.commit()
        conn.close()


def _q(sql: str, args: tuple = ()) -> list[sqlite3.Row]:
    with _lock:
        conn = get_conn()
        try:
            rows = conn.execute(sql, args).fetchall()
        finally:
            conn.close()
        return rows


def _exec(sql: str, args: tuple = ()) -> int:
    with _lock:
        conn = get_conn()
        try:
            cur = conn.execute(sql, args)
            conn.commit()
            return cur.lastrowid
        finally:
            conn.close()


# ---------- categories ----------

def list_categories() -> list[dict]:
    rows = _q(
        """
        SELECT c.*, (SELECT COUNT(*) FROM sites s WHERE s.category_id = c.id) AS site_count
        FROM categories c ORDER BY c.sort_order, c.id
        """
    )
    return [dict(r) for r in rows]


def create_category(name: str, icon: str = "") -> dict:
    cid = _exec(
        "INSERT INTO categories (name, icon) VALUES (?, ?)",
        (name.strip(), icon),
    )
    return get_category(cid)


def get_category(cid: int) -> dict | None:
    rows = _q(
        "SELECT c.*, (SELECT COUNT(*) FROM sites s WHERE s.category_id = c.id) AS site_count FROM categories c WHERE c.id = ?",
        (cid,),
    )
    return dict(rows[0]) if rows else None


def update_category(cid: int, name: str | None = None, icon: str | None = None, sort_order: int | None = None) -> bool:
    fields, args = [], []
    if name is not None:
        fields.append("name = ?")
        args.append(name.strip())
    if icon is not None:
        fields.append("icon = ?")
        args.append(icon)
    if sort_order is not None:
        fields.append("sort_order = ?")
        args.append(int(sort_order))
    if not fields:
        return False
    args.append(cid)
    _exec(f"UPDATE categories SET {', '.join(fields)} WHERE id = ?", tuple(args))
    return True


def delete_category(cid: int) -> None:
    # 站点置为未分类（category_id NULL）
    _exec("UPDATE sites SET category_id = NULL WHERE category_id = ?", (cid,))
    _exec("DELETE FROM categories WHERE id = ?", (cid,))


# ---------- sites ----------

def list_sites(category_id: int | None = None, tag: str | None = None) -> list[dict]:
    sql = "SELECT * FROM sites"
    args: list = []
    conds = []
    if category_id is not None:
        conds.append("category_id = ?")
        args.append(category_id)
    if tag:
        conds.append("',' || tags || ',' LIKE ?")
        args.append(f"%,{tag.strip()},%")
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY pinned DESC, sort_order, id"
    return [dict(r) for r in _q(sql, tuple(args))]


def get_site(sid: int) -> dict | None:
    rows = _q("SELECT * FROM sites WHERE id = ?", (sid,))
    return dict(rows[0]) if rows else None


def create_site(category_id: int | None, title: str, url: str, description: str = "", favicon: str = "", tags: str = "") -> dict:
    sid = _exec(
        "INSERT INTO sites (category_id, title, url, description, favicon, tags) VALUES (?, ?, ?, ?, ?, ?)",
        (category_id, title.strip(), url.strip(), description, favicon, tags.strip()),
    )
    return get_site(sid)


def update_site(
    sid: int,
    category_id: int | None = None,
    title: str | None = None,
    url: str | None = None,
    description: str | None = None,
    favicon: str | None = None,
    tags: str | None = None,
    sort_order: int | None = None,
    pinned: int | None = None,
) -> bool:
    fields, args = [], []
    if category_id is not None:
        fields.append("category_id = ?")
        args.append(category_id)
    if title is not None:
        fields.append("title = ?")
        args.append(title.strip())
    if url is not None:
        fields.append("url = ?")
        args.append(url.strip())
    if description is not None:
        fields.append("description = ?")
        args.append(description)
    if favicon is not None:
        fields.append("favicon = ?")
        args.append(favicon)
    if tags is not None:
        fields.append("tags = ?")
        args.append(tags.strip())
    if sort_order is not None:
        fields.append("sort_order = ?")
        args.append(int(sort_order))
    if pinned is not None:
        fields.append("pinned = ?")
        args.append(1 if pinned else 0)
    if not fields:
        return False
    args.append(sid)
    _exec(f"UPDATE sites SET {', '.join(fields)} WHERE id = ?", tuple(args))
    return True


def delete_site(sid: int) -> None:
    _exec("DELETE FROM sites WHERE id = ?", (sid,))


# ---------- 死链检测 & 点击统计 ----------

def set_site_status(sid: int, status: str) -> None:
    _exec(
        "UPDATE sites SET status = ?, status_at = datetime('now') WHERE id = ?",
        (status, sid),
    )


def increment_clicks(sid: int) -> None:
    _exec("UPDATE sites SET clicks = clicks + 1 WHERE id = ?", (sid,))


def top_sites(limit: int = 8) -> list[dict]:
    return [dict(r) for r in _q(
        "SELECT * FROM sites WHERE clicks > 0 ORDER BY clicks DESC LIMIT ?",
        (limit,),
    )]


# ---------- settings ----------

def get_setting(key: str, default: str = "") -> str:
    rows = _q("SELECT value FROM settings WHERE key = ?", (key,))
    return rows[0]["value"] if rows else default


def all_settings() -> dict:
    rows = _q("SELECT key, value FROM settings")
    return {r["key"]: r["value"] for r in rows}


def set_setting(key: str, value: str) -> None:
    _exec(
        "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )


# ---------- notes（便签） ----------

def list_notes() -> list[dict]:
    rows = _q("SELECT * FROM notes ORDER BY sort_order, id DESC")
    return [dict(r) for r in rows]


def get_note(nid: int) -> dict | None:
    rows = _q("SELECT * FROM notes WHERE id = ?", (nid,))
    return dict(rows[0]) if rows else None


def create_note(content: str) -> dict:
    # 新便签排最前（sort_order = 0，其余顺延）
    with _lock:
        conn = get_conn()
        try:
            conn.execute("UPDATE notes SET sort_order = sort_order + 1")
            cur = conn.execute("INSERT INTO notes (content, sort_order) VALUES (?, 0)", (content.strip(),))
            nid = cur.lastrowid
            conn.commit()
        finally:
            conn.close()
    return get_note(nid)


def reorder_notes(order: list[int]) -> None:
    """order 是便签 id 数组，按顺序写 sort_order。"""
    with _lock:
        conn = get_conn()
        try:
            for i, nid in enumerate(order):
                conn.execute("UPDATE notes SET sort_order = ? WHERE id = ?", (i, nid))
            conn.commit()
        finally:
            conn.close()


def update_note(nid: int, content: str) -> bool:
    _exec(
        "UPDATE notes SET content = ?, updated_at = datetime('now', 'localtime') WHERE id = ?",
        (content.strip(), nid),
    )
    return True


def delete_note(nid: int) -> None:
    _exec("DELETE FROM notes WHERE id = ?", (nid,))


# ---------- mail_codes（邮箱验证码速取） ----------

def add_mail_code(sender: str, subject: str, code: str, mail_time: str = "") -> bool:
    """新增验证码记录；同 sender+code+mail_time 视为重复，返回是否新增。"""
    rows = _q(
        "SELECT id FROM mail_codes WHERE sender = ? AND code = ? AND mail_time = ?",
        (sender, code, mail_time),
    )
    if rows:
        return False
    _exec(
        "INSERT INTO mail_codes (sender, subject, code, mail_time) VALUES (?, ?, ?, ?)",
        (sender, subject, code, mail_time),
    )
    return True


def list_mail_codes(limit: int = 20) -> list[dict]:
    rows = _q("SELECT * FROM mail_codes ORDER BY id DESC LIMIT ?", (limit,))
    return [dict(r) for r in rows]


def unread_mail_codes() -> list[dict]:
    rows = _q("SELECT * FROM mail_codes WHERE is_read = 0 ORDER BY id DESC LIMIT 10")
    return [dict(r) for r in rows]


def mark_mail_codes_read() -> None:
    _exec("UPDATE mail_codes SET is_read = 1 WHERE is_read = 0")


def delete_mail_code(cid: int) -> None:
    _exec("DELETE FROM mail_codes WHERE id = ?", (cid,))


def cleanup_mail_codes(hours: int = 48, keep: int = 3) -> None:
    """验证码只用一次：清理超过 hours 小时的记录，且最多保留 keep 条（默认最近 3 条）。"""
    _exec(
        "DELETE FROM mail_codes WHERE fetched_at < datetime('now', 'localtime', ?)",
        (f"-{int(hours)} hours",),
    )
    _exec(
        "DELETE FROM mail_codes WHERE id NOT IN (SELECT id FROM mail_codes ORDER BY id DESC LIMIT ?)",
        (int(keep),),
    )
