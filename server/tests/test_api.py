"""NavHub 后端冒烟测试。"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

import db
import main

db.DB_PATH = db.Path(db.__file__).parent / "test_navhub.db"
if db.DB_PATH.exists():
    db.DB_PATH.unlink()
db.init_db()

client = TestClient(main.app)


@pytest.fixture(scope="module", autouse=True)
def login():
    r = client.post("/api/auth/login", json={"password": "admin123456"})
    assert r.status_code == 200, r.text
    yield


def test_auth_required():
    # 用无 cookie 的新客户端验证未登录拦截
    anon = TestClient(main.app)
    r = anon.get("/api/categories")
    assert r.status_code == 401


def test_login_wrong_password():
    r = client.post("/api/auth/login", json={"password": "wrong"})
    assert r.status_code == 401


def test_category_crud():
    r = client.post("/api/categories", json={"name": "AI 工具", "icon": "🤖"})
    assert r.status_code == 200
    cid = r.json()["id"]

    r = client.get("/api/categories")
    assert any(c["name"] == "AI 工具" for c in r.json())

    r = client.patch(f"/api/categories/{cid}", json={"name": "AI 工具2"})
    assert r.json()["name"] == "AI 工具2"

    r = client.delete(f"/api/categories/{cid}")
    assert r.json()["ok"] is True


def test_site_crud():
    r = client.post("/api/categories", json={"name": "测试分类"})
    cid = r.json()["id"]

    r = client.post("/api/sites", json={"category_id": cid, "title": "GitHub", "url": "https://github.com"})
    assert r.status_code == 200, r.text
    sid = r.json()["id"]

    r = client.get("/api/sites", params={"category_id": cid})
    assert len(r.json()) == 1

    r = client.patch(f"/api/sites/{sid}", json={"title": "GitHub2"})
    assert r.json()["title"] == "GitHub2"

    r = client.delete(f"/api/sites/{sid}")
    assert r.json()["ok"] is True


def test_duplicate_url_rejected():
    client.post("/api/sites", json={"title": "A", "url": "https://example.com/a"})
    r = client.post("/api/sites", json={"title": "B", "url": "https://example.com/a"})
    assert r.status_code == 400


def test_classify_no_categories():
    # 清空分类，模拟"还没有分类"状态
    for c in client.get("/api/categories").json():
        client.delete(f"/api/categories/{c['id']}")
    r = client.post("/api/sites/ai-classify", json={"url": "https://example.com"})
    assert r.status_code == 200
    data = r.json()
    assert data["suggestion"]["category"] is None
    # 未配置 AI key 时优先提示 key 缺失；配置了 key 且无分类时提示建分类
    assert ("还没有分类" in data["suggestion"]["reason"]) or ("未配置 AI API key" in data["suggestion"]["reason"])
