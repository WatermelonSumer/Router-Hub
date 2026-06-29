"""坟场接口测试。

覆盖：suspected/dead 分流、按 status_changed_at 倒序、非坟场态不出现、
无 key/base_url 泄露、空坟场返回两空列表。
"""

from datetime import timedelta

from tortoise import timezone

from app.models.relay_site import RelaySite

_SECRET_KEY = "sk-graveyard-secret-7777"
_BASE_URL = "https://internal.graveyard.example/v1"


async def _make_site(slug, status, *, days_ago=1, name="DeadHub", models=None) -> RelaySite:
    """直接造一个站点，key/base_url 为敏感值用于泄露断言。"""
    return await RelaySite.create(
        owner_id="00000000-0000-0000-0000-0000000000bb",
        name=name,
        slug=slug,
        base_url=_BASE_URL,
        encrypted_key="ENCRYPTED::" + _SECRET_KEY,
        key_hint="sk-***7777",
        status=status,
        declared_models=models or ["gpt-4o"],
        first_seen_at=timezone.now() - timedelta(days=60),
        last_probe_at=timezone.now() - timedelta(days=days_ago),
        status_changed_at=timezone.now() - timedelta(days=days_ago),
    )


async def test_graveyard_splits_suspected_and_dead(client):
    """疑似/已阵亡分流到两区。"""
    await _make_site("susp-1", "suspected_dead", name="SuspectHub")
    await _make_site("dead-1", "dead", name="GoneHub")

    resp = await client.get("/graveyard")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["suspected"]) == 1
    assert len(body["dead"]) == 1
    assert body["suspected"][0]["name"] == "SuspectHub"
    assert body["dead"][0]["name"] == "GoneHub"


async def test_graveyard_excludes_living_sites(client):
    """在线/观察/待审等非坟场态不出现在坟场。"""
    await _make_site("online-1", "online")
    await _make_site("observing-1", "observing")
    await _make_site("pending-1", "pending")
    await _make_site("dead-2", "dead", name="OnlyDead")

    resp = await client.get("/graveyard")
    body = resp.json()
    assert body["suspected"] == []
    assert len(body["dead"]) == 1
    assert body["dead"][0]["name"] == "OnlyDead"


async def test_graveyard_orders_by_status_changed_desc(client):
    """同区内按进入坟场时间倒序，最近的置顶。"""
    await _make_site("dead-old", "dead", days_ago=10, name="OldDead")
    await _make_site("dead-new", "dead", days_ago=1, name="RecentDead")

    resp = await client.get("/graveyard")
    dead = resp.json()["dead"]
    assert [s["name"] for s in dead] == ["RecentDead", "OldDead"]


async def test_graveyard_no_key_or_base_url_leak(client):
    """红线：坟场响应绝不泄露 key / base_url。"""
    await _make_site("leak-check", "dead")

    resp = await client.get("/graveyard")
    entry = resp.json()["dead"][0]
    assert _SECRET_KEY not in resp.text
    assert _BASE_URL not in resp.text
    assert "base_url" not in entry
    assert "encrypted_key" not in entry
    assert "key_hint" not in entry
    # status_changed_at 应暴露（前端算「连续失败 N 天」用）
    assert entry["status_changed_at"] is not None


async def test_graveyard_empty(client):
    """无坟场站点时返回两个空列表。"""
    await _make_site("alive-only", "online")

    resp = await client.get("/graveyard")
    body = resp.json()
    assert body == {"suspected": [], "dead": []}
