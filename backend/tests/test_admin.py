"""管理员审核接口测试：列待审、通过→observing、驳回→rejected+理由、权限、重复审核。"""

from app.core.security import hash_password
from app.models.user import User


async def _register_owner(client, email: str):
    """注册站长并返回鉴权 headers。"""
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": "owner",
            "wechat": "wx_test",
            "qq": "10001",
        },
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _login_admin(client, email: str = "admin@test.com"):
    """直接造一个 admin 用户（注册接口造不出），登录拿 headers。"""
    await User.create(email=email, password_hash=hash_password("adminpass1"), role="admin")
    resp = await client.post("/auth/login", json={"email": email, "password": "adminpass1"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _create_site(client, owner_headers, name="ClaudeHub"):
    """站长上架一个站点，返回其响应体。"""
    resp = await client.post(
        "/sites",
        headers=owner_headers,
        json={
            "name": name,
            "base_url": "https://api.example.com/v1",
            "api_key": "sk-abcdefgh1234",
        },
    )
    assert resp.status_code == 201
    return resp.json()


async def test_admin_list_pending(client):
    """管理员能列出待审站点，含站长联系方式，且不含 key。"""
    owner_headers = await _register_owner(client, "owner1@example.com")
    await _create_site(client, owner_headers)
    admin_headers = await _login_admin(client)

    resp = await client.get("/admin/sites/pending", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    item = items[0]
    assert item["status"] == "pending"
    assert item["owner_email"] == "owner1@example.com"
    assert item["owner_wechat"] == "wx_test"
    # 红线：审核视角也绝不含 key
    assert "encrypted_key" not in item
    assert "sk-abcdefgh1234" not in resp.text


async def test_admin_approve(client):
    """通过审核：pending → observing，review_note 为空。"""
    owner_headers = await _register_owner(client, "owner2@example.com")
    site = await _create_site(client, owner_headers)
    admin_headers = await _login_admin(client)

    resp = await client.post(
        f"/admin/sites/{site['site_id']}/approve", headers=admin_headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "observing"
    assert body["review_note"] is None

    # 站长侧也能看到状态已变
    mine = await client.get("/sites/mine", headers=owner_headers)
    assert mine.json()[0]["status"] == "observing"


async def test_admin_reject_with_note(client):
    """驳回审核：pending → rejected，理由写入并对站长可见。"""
    owner_headers = await _register_owner(client, "owner3@example.com")
    site = await _create_site(client, owner_headers)
    admin_headers = await _login_admin(client)

    resp = await client.post(
        f"/admin/sites/{site['site_id']}/reject",
        headers=admin_headers,
        json={"note": "base_url 无法连通"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"

    mine = await client.get("/sites/mine", headers=owner_headers)
    rejected = mine.json()[0]
    assert rejected["status"] == "rejected"
    assert rejected["review_note"] == "base_url 无法连通"


async def test_reject_requires_note(client):
    """驳回必须给理由：空 note 返回 422。"""
    owner_headers = await _register_owner(client, "owner4@example.com")
    site = await _create_site(client, owner_headers)
    admin_headers = await _login_admin(client)

    resp = await client.post(
        f"/admin/sites/{site['site_id']}/reject",
        headers=admin_headers,
        json={"note": ""},
    )
    assert resp.status_code == 422


async def test_double_review_conflicts(client):
    """重复审核已离开 pending 的站点返回 409。"""
    owner_headers = await _register_owner(client, "owner5@example.com")
    site = await _create_site(client, owner_headers)
    admin_headers = await _login_admin(client)

    first = await client.post(
        f"/admin/sites/{site['site_id']}/approve", headers=admin_headers
    )
    assert first.status_code == 200
    again = await client.post(
        f"/admin/sites/{site['site_id']}/approve", headers=admin_headers
    )
    assert again.status_code == 409


async def test_approve_missing_site_404(client):
    """审核不存在的站点返回 404。"""
    admin_headers = await _login_admin(client)
    resp = await client.post(
        "/admin/sites/00000000-0000-0000-0000-000000000000/approve",
        headers=admin_headers,
    )
    assert resp.status_code == 404


async def test_owner_cannot_access_admin(client):
    """站长访问审核接口返回 403。"""
    owner_headers = await _register_owner(client, "owner6@example.com")
    resp = await client.get("/admin/sites/pending", headers=owner_headers)
    assert resp.status_code == 403


async def test_admin_endpoints_require_auth(client):
    """未登录访问审核接口返回 401。"""
    resp = await client.get("/admin/sites/pending")
    assert resp.status_code == 401


async def test_admin_list_by_status_observing(client):
    """审核通过后的站点能在 status=observing 的总览中查到（含站长联系方式，不含 key）。"""
    owner_headers = await _register_owner(client, "owner7@example.com")
    site = await _create_site(client, owner_headers, name="ObserveHub")
    admin_headers = await _login_admin(client, "admin7@test.com")
    await client.post(f"/admin/sites/{site['site_id']}/approve", headers=admin_headers)

    resp = await client.get("/admin/sites?status=observing", headers=admin_headers)
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["name"] == "ObserveHub"
    assert items[0]["status"] == "observing"
    assert items[0]["owner_email"] == "owner7@example.com"
    # 红线：仍不含 key
    assert "encrypted_key" not in items[0]
    assert "sk-abcdefgh1234" not in resp.text


async def test_admin_list_by_status_default_observing(client):
    """status 缺省时默认列 observing（pending 站不应出现）。"""
    owner_headers = await _register_owner(client, "owner8@example.com")
    await _create_site(client, owner_headers)  # 留在 pending
    admin_headers = await _login_admin(client, "admin8@test.com")

    resp = await client.get("/admin/sites", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


async def test_admin_list_by_status_invalid_422(client):
    """非法状态值返回 422。"""
    admin_headers = await _login_admin(client, "admin9@test.com")
    resp = await client.get("/admin/sites?status=nonsense", headers=admin_headers)
    assert resp.status_code == 422


async def test_admin_list_by_status_requires_admin(client):
    """站长访问总览接口返回 403。"""
    owner_headers = await _register_owner(client, "owner10@example.com")
    resp = await client.get("/admin/sites?status=observing", headers=owner_headers)
    assert resp.status_code == 403
