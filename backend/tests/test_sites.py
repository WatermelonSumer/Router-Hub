"""中转站上架接口测试：站长上架、编辑、下架、key 不外泄、权限校验。"""

from tortoise import timezone

from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore


async def _register(client, email: str, role: str = "owner"):
    """注册并返回 (token, headers)；站长补微信/QQ。"""
    payload = {"email": email, "password": "password123", "role": role}
    if role == "owner":
        payload["wechat"] = "wx_test"
        payload["qq"] = "10001"
    resp = await client.post("/auth/register", json=payload)
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return token, {"Authorization": f"Bearer {token}"}


async def test_owner_create_site(client):
    """站长上架成功，响应含 key_hint 与 pending 状态，且不含明文/密文 key。"""
    _, headers = await _register(client, "owner_a@example.com")
    resp = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "ClaudeHub",
            "base_url": "https://api.claudehub.example/v1",
            "api_key": "sk-abcdefgh1234",
            "declared_models": ["claude-3-5-sonnet"],
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "ClaudeHub"
    assert body["slug"] == "claudehub"  # 由 name 生成
    assert body["status"] == "pending"
    assert body["key_hint"] == "sk-***1234"
    # 红线：响应绝不含 key 任何形态
    assert "api_key" not in body
    assert "encrypted_key" not in body
    assert "sk-abcdefgh1234" not in resp.text


async def test_create_site_custom_slug_and_conflict(client):
    """站长指定 slug 成功；重复 slug 返回 409。"""
    _, headers = await _register(client, "owner_b@example.com")
    first = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "My Relay",
            "base_url": "https://api.relay.example/v1",
            "api_key": "sk-key1234567",
            "slug": "my-relay",
        },
    )
    assert first.status_code == 201
    assert first.json()["slug"] == "my-relay"

    dup = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "Another",
            "base_url": "https://api.other.example/v1",
            "api_key": "sk-key7654321",
            "slug": "my-relay",
        },
    )
    assert dup.status_code == 409


async def test_auto_slug_dedup(client):
    """同名站点自动生成的 slug 不冲突（追加后缀）。"""
    _, headers = await _register(client, "owner_c@example.com")
    body1 = (
        await client.post(
            "/sites",
            headers=headers,
            json={"name": "Relay", "base_url": "https://a.example/v1", "api_key": "sk-aaa11112222"},
        )
    ).json()
    body2 = (
        await client.post(
            "/sites",
            headers=headers,
            json={"name": "Relay", "base_url": "https://b.example/v1", "api_key": "sk-bbb11112222"},
        )
    ).json()
    assert body1["slug"] != body2["slug"]


async def test_list_mine(client):
    """站长能列出自己上架的全部站点。"""
    _, headers = await _register(client, "owner_d@example.com")
    for i in range(2):
        await client.post(
            "/sites",
            headers=headers,
            json={
                "name": f"Site{i}",
                "base_url": f"https://s{i}.example/v1",
                "api_key": f"sk-site{i}1234567",
            },
        )
    resp = await client.get("/sites/mine", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_user_cannot_create_site(client):
    """普通用户上架返回 403。"""
    _, headers = await _register(client, "plain_user@example.com", role="user")
    resp = await client.post(
        "/sites",
        headers=headers,
        json={"name": "X", "base_url": "https://x.example/v1", "api_key": "sk-xxxxxxxxxxx"},
    )
    assert resp.status_code == 403


async def test_create_site_requires_auth(client):
    """未登录上架返回 401。"""
    resp = await client.post(
        "/sites",
        json={"name": "X", "base_url": "https://x.example/v1", "api_key": "sk-xxxxxxxxxxx"},
    )
    assert resp.status_code == 401


async def test_update_display_fields_keeps_current_status(client):
    """编辑展示/硬信息不退回待审，也不更换 key 掩码。"""
    _, headers = await _register(client, "owner_edit_display@example.com")
    created = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "DisplayRelay",
            "base_url": "https://old.example/v1",
            "api_key": "sk-old12345678",
        },
    )
    site_id = created.json()["site_id"]
    site = await RelaySite.get(site_id=site_id)
    site.status = "online"
    site.status_changed_at = timezone.now()
    await site.save(update_fields=["status", "status_changed_at", "updated_at"])

    resp = await client.patch(
        f"/sites/{site_id}",
        headers=headers,
        json={
            "name": "DisplayRelay Pro",
            "site_url": "https://relay.example",
            "min_topup": "20.00",
            "pay_methods": "支付宝, USDT",
            "rpm_limit": 300,
            "probe_budget_daily": 9,
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "DisplayRelay Pro"
    assert body["status"] == "online"
    assert body["key_hint"] == "sk-***5678"
    assert body["probe_budget_daily"] == 9


async def test_update_probe_identity_resets_review_and_clears_old_probe_data(client):
    """变更 Base URL / API Key / 声明模型后退回 pending，并软删除旧探测事实与分数。"""
    _, headers = await _register(client, "owner_edit_identity@example.com")
    created = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "IdentityRelay",
            "base_url": "https://old.example/v1",
            "api_key": "sk-old12345678",
            "declared_models": ["gpt-4o"],
        },
    )
    site_id = created.json()["site_id"]
    site = await RelaySite.get(site_id=site_id)
    now = timezone.now()
    site.status = "online"
    site.review_note = "old note"
    site.status_changed_at = now
    site.first_seen_at = now
    site.last_probe_at = now
    await site.save(
        update_fields=[
            "status",
            "review_note",
            "status_changed_at",
            "first_seen_at",
            "last_probe_at",
            "updated_at",
        ]
    )
    await ProbeResult.create(
        site_id=site.site_id,
        probe_type="alive",
        probed_at=now,
        is_alive=True,
    )
    await SiteScore.create(
        site_id=site.site_id,
        leaderboard="gpt",
        uptime_score=90,
        composite_score=90,
        rank=1,
    )

    resp = await client.patch(
        f"/sites/{site_id}",
        headers=headers,
        json={
            "base_url": "https://new.example/v1",
            "api_key": "sk-new87654321",
            "declared_models": ["claude-3-5-sonnet"],
        },
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["review_note"] is None
    assert body["base_url"] == "https://new.example/v1"
    assert body["key_hint"] == "sk-***4321"
    assert body["declared_models"] == ["claude-3-5-sonnet"]
    assert await ProbeResult.filter(site_id=site.site_id).count() == 0
    assert await SiteScore.filter(site_id=site.site_id).count() == 0
    assert (
        await ProbeResult.all_objects().filter(site_id=site.site_id, is_deleted=True).count() == 1
    )
    assert await SiteScore.all_objects().filter(site_id=site.site_id, is_deleted=True).count() == 1


async def test_other_owner_cannot_update_or_delete_site(client):
    """站点编辑/下架只允许归属站长操作，越权统一返回 404。"""
    _, owner_headers = await _register(client, "owner_acl_a@example.com")
    _, other_headers = await _register(client, "owner_acl_b@example.com")
    created = await client.post(
        "/sites",
        headers=owner_headers,
        json={
            "name": "AclRelay",
            "base_url": "https://acl.example/v1",
            "api_key": "sk-acl12345678",
        },
    )
    site_id = created.json()["site_id"]

    update_resp = await client.patch(
        f"/sites/{site_id}",
        headers=other_headers,
        json={"name": "Stolen"},
    )
    delete_resp = await client.delete(f"/sites/{site_id}", headers=other_headers)

    assert update_resp.status_code == 404
    assert delete_resp.status_code == 404


async def test_owner_delete_site_soft_deletes_and_hides_public_detail(client):
    """站长下架站点后，自己的列表和公开详情都不可见。"""
    _, headers = await _register(client, "owner_delete@example.com")
    created = await client.post(
        "/sites",
        headers=headers,
        json={
            "name": "DeleteRelay",
            "base_url": "https://delete.example/v1",
            "api_key": "sk-delete123456",
        },
    )
    body = created.json()
    site = await RelaySite.get(site_id=body["site_id"])
    site.status = "online"
    await site.save(update_fields=["status", "updated_at"])

    resp = await client.delete(f"/sites/{body['site_id']}", headers=headers)

    assert resp.status_code == 204
    assert (await client.get("/sites/mine", headers=headers)).json() == []
    assert (await client.get(f"/sites/{body['slug']}")).status_code == 404
    assert (
        await RelaySite.all_objects().filter(site_id=body["site_id"], is_deleted=True).count() == 1
    )
