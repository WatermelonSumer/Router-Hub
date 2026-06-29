"""站点详情接口测试。

覆盖：公开详情字段 + 无 key/base_url 泄露、在线率分桶（含维护窗剔除）、
verified 标记、各榜分摘要、404（pending/不存在）、gated 401 无 token /
登录可见硬信息 + 仍不泄露 key。
"""

from datetime import timedelta

from tortoise import timezone

from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore

_SECRET_KEY = "sk-supersecret-9999"
_BASE_URL = "https://internal.example.com/v1"


async def _register_user(client, email: str, role: str = "user"):
    """注册用户（默认普通用户），返回鉴权 headers。"""
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": role},
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _make_site(slug="hub", status="online", **kwargs) -> RelaySite:
    """直接造一个站点（绕过审核流程），key/base_url 为敏感值用于泄露断言。"""
    return await RelaySite.create(
        owner_id="00000000-0000-0000-0000-0000000000aa",
        name=kwargs.get("name", "DetailHub"),
        slug=slug,
        base_url=_BASE_URL,
        encrypted_key="ENCRYPTED::" + _SECRET_KEY,
        key_hint="sk-***9999",
        status=status,
        declared_models=kwargs.get("models", ["claude-3-5-sonnet", "gpt-4o"]),
        min_topup=kwargs.get("min_topup"),
        pay_methods=kwargs.get("pay_methods"),
        rpm_limit=kwargs.get("rpm_limit"),
        maintenance_windows=kwargs.get("maintenance_windows"),
        first_seen_at=timezone.now() - timedelta(days=10),
        last_probe_at=timezone.now(),
    )


async def _probe(site, *, days_ago, alive, ptype="alive", authentic=None, ttfb=None):
    """造一条探测结果，probed_at 落在 days_ago 天前。"""
    await ProbeResult.create(
        site_id=site.site_id,
        probe_type=ptype,
        probed_at=timezone.now() - timedelta(days=days_ago),
        is_alive=alive,
        is_authentic=authentic,
        ttfb_ms=ttfb,
    )


async def test_public_detail_basic(client):
    """公开详情返回游客字段，且绝不泄露 key / base_url。"""
    site = await _make_site(slug="basic-hub")
    await SiteScore.create(
        site_id=site.site_id,
        leaderboard="claude",
        composite_score=91.5,
        rank=2,
    )

    resp = await client.get("/sites/basic-hub")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "DetailHub"
    assert body["slug"] == "basic-hub"
    assert body["status"] == "online"
    assert body["declared_models"] == ["claude-3-5-sonnet", "gpt-4o"]
    assert body["listed_at"] is not None
    assert body["scores"] == [
        {"leaderboard": "claude", "composite_score": 91.5, "rank": 2}
    ]
    # 红线：绝不泄露 key / base_url / 加密串
    assert _SECRET_KEY not in resp.text
    assert _BASE_URL not in resp.text
    assert "encrypted_key" not in body
    assert "base_url" not in body
    assert "key_hint" not in body


async def test_public_detail_uptime_history(client):
    """在线率曲线逐日分桶正确，总在线率按样本汇总。"""
    site = await _make_site(slug="uptime-hub")
    # 1 天前：3 次探测，2 alive → 当天 66.7%
    await _probe(site, days_ago=1, alive=True)
    await _probe(site, days_ago=1, alive=True)
    await _probe(site, days_ago=1, alive=False)
    # 2 天前：2 次全 alive → 100%
    await _probe(site, days_ago=2, alive=True)
    await _probe(site, days_ago=2, alive=True)

    resp = await client.get("/sites/uptime-hub")
    body = resp.json()
    assert len(body["uptime_history"]) == 30
    # 总在线率：4 alive / 5 total = 80%
    assert body["uptime_30d"] == 80.0
    by_date = {p["date"]: p["uptime"] for p in body["uptime_history"]}
    today = timezone.now().date()
    d1 = (today - timedelta(days=1)).isoformat()
    d2 = (today - timedelta(days=2)).isoformat()
    assert by_date[d1] == 66.7
    assert by_date[d2] == 100.0
    # 无样本的天为 None（断点，不画成 0）
    d5 = (today - timedelta(days=5)).isoformat()
    assert by_date[d5] is None


async def test_uptime_excludes_maintenance_window_failures(client):
    """维护窗内的失败整条剔除，不拉低在线率（与状态机红线一致）。"""
    now = timezone.now()
    win_start = (now - timedelta(days=1, hours=1)).isoformat()
    win_end = (now - timedelta(days=1) + timedelta(hours=1)).isoformat()
    site = await _make_site(
        slug="maint-hub",
        maintenance_windows=[{"start": win_start, "end": win_end}],
    )
    # 1 天前两次探测都落在维护窗内：1 成功 + 1 失败。失败应被剔除 → 当天 100%
    await _probe(site, days_ago=1, alive=True)
    await _probe(site, days_ago=1, alive=False)

    resp = await client.get("/sites/maint-hub")
    body = resp.json()
    assert body["uptime_30d"] == 100.0


async def test_public_detail_verified_flag(client):
    """有成功质量探测 → verified=True。"""
    site = await _make_site(slug="verified-hub")
    await _probe(site, days_ago=1, alive=True, ptype="quality", authentic=True, ttfb=300)

    resp = await client.get("/sites/verified-hub")
    assert resp.json()["verified"] is True


async def test_public_detail_not_verified_without_quality(client):
    """无成功质量探测 → verified=False。"""
    site = await _make_site(slug="plain-hub")
    await _probe(site, days_ago=1, alive=True)

    resp = await client.get("/sites/plain-hub")
    assert resp.json()["verified"] is False


async def test_public_detail_pending_404(client):
    """未审核（pending）站点不对外公开，返回 404。"""
    await _make_site(slug="pending-hub", status="pending")
    resp = await client.get("/sites/pending-hub")
    assert resp.status_code == 404


async def test_public_detail_unknown_404(client):
    """不存在的 slug 返回 404。"""
    resp = await client.get("/sites/no-such-site")
    assert resp.status_code == 404


async def test_gated_requires_auth(client):
    """硬信息接口未登录返回 401。"""
    await _make_site(slug="gated-hub")
    resp = await client.get("/sites/gated-hub/private")
    assert resp.status_code == 401


async def test_gated_detail_for_logged_in_user(client):
    """登录用户可见硬信息 + TTFB 分位，且仍不泄露 key / base_url。"""
    site = await _make_site(
        slug="paid-hub",
        min_topup="50.00",
        pay_methods="支付宝 / USDT",
        rpm_limit=120,
    )
    # 三条成功质量探测，TTFB 100/200/300
    await _probe(site, days_ago=1, alive=True, ptype="quality", authentic=True, ttfb=100)
    await _probe(site, days_ago=1, alive=True, ptype="quality", authentic=True, ttfb=200)
    await _probe(site, days_ago=1, alive=True, ptype="quality", authentic=True, ttfb=300)

    headers = await _register_user(client, "viewer@example.com")
    resp = await client.get("/sites/paid-hub/private", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["pay_methods"] == "支付宝 / USDT"
    assert body["rpm_limit"] == 120
    assert body["latency_samples"] == 3
    assert body["ttfb_p50_ms"] is not None
    assert body["ttfb_p90_ms"] is not None
    # 红线：硬信息接口也绝不泄露 key / base_url
    assert _SECRET_KEY not in resp.text
    assert _BASE_URL not in resp.text


async def test_gated_detail_unknown_404(client):
    """登录后访问不存在站点的硬信息返回 404。"""
    headers = await _register_user(client, "viewer2@example.com")
    resp = await client.get("/sites/no-such-site/private", headers=headers)
    assert resp.status_code == 404
