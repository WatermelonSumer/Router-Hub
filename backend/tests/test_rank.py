"""排行榜接口测试：排序、主榜/观察区分流、坟场不上榜、公开安全、非法参数。

直接造 RelaySite + SiteScore（绕过探测 worker），验证读取与分流逻辑。
"""

from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore


async def _make_site(name: str, status: str = "online") -> RelaySite:
    """造一个站点（key 字段填占位，测试不涉及探测）。"""
    return await RelaySite.create(
        owner_id="00000000-0000-0000-0000-000000000001",
        name=name,
        slug=name.lower().replace(" ", "-"),
        base_url=f"https://{name.lower()}.example/v1",
        encrypted_key="enc",
        key_hint="sk-***0000",
        status=status,
    )


async def _make_score(site: RelaySite, leaderboard: str, **scores) -> SiteScore:
    """为某站某榜造一行预计算分。"""
    return await SiteScore.create(
        site_id=site.site_id,
        leaderboard=leaderboard,
        **scores,
    )


async def test_rank_default_sort_composite(client):
    """默认按综合分降序。"""
    a = await _make_site("Alpha")
    b = await _make_site("Bravo")
    await _make_score(a, "claude", composite_score=80, rank=2)
    await _make_score(b, "claude", composite_score=95, rank=1)

    resp = await client.get("/rank?leaderboard=claude")
    assert resp.status_code == 200
    body = resp.json()
    names = [e["name"] for e in body["main"]]
    assert names == ["Bravo", "Alpha"]


async def test_rank_sort_by_speed(client):
    """sort=speed 时按速度分降序，与综合分顺序不同。"""
    a = await _make_site("Alpha")
    b = await _make_site("Bravo")
    await _make_score(a, "gpt", composite_score=80, speed_score=99)
    await _make_score(b, "gpt", composite_score=95, speed_score=10)

    resp = await client.get("/rank?leaderboard=gpt&sort=speed")
    assert resp.status_code == 200
    names = [e["name"] for e in resp.json()["main"]]
    assert names == ["Alpha", "Bravo"]


async def test_observing_separated_from_main(client):
    """observing 站点进观察区，不进主榜。"""
    online = await _make_site("OnlineSite", status="online")
    newbie = await _make_site("NewSite", status="observing")
    await _make_score(online, "gemini", composite_score=70)
    await _make_score(newbie, "gemini", composite_score=88)

    body = (await client.get("/rank?leaderboard=gemini")).json()
    assert [e["name"] for e in body["main"]] == ["OnlineSite"]
    assert [e["name"] for e in body["observing"]] == ["NewSite"]


async def test_graveyard_status_not_listed(client):
    """坟场状态（dead/suspected_dead）不上任何榜。"""
    dead = await _make_site("DeadSite", status="dead")
    suspected = await _make_site("SuspectedSite", status="suspected_dead")
    await _make_score(dead, "claude", composite_score=50)
    await _make_score(suspected, "claude", composite_score=60)

    body = (await client.get("/rank?leaderboard=claude")).json()
    assert body["main"] == []
    assert body["observing"] == []


async def test_null_scores_sort_last(client):
    """某指标无数据（null）的站排在有数据的后面。"""
    has = await _make_site("HasSpeed")
    none = await _make_site("NoSpeed")
    await _make_score(has, "gpt", composite_score=50, speed_score=40)
    await _make_score(none, "gpt", composite_score=90, speed_score=None)

    body = (await client.get("/rank?leaderboard=gpt&sort=speed")).json()
    assert [e["name"] for e in body["main"]] == ["HasSpeed", "NoSpeed"]


async def test_rank_public_safe(client):
    """榜单响应只含公开字段，绝不含 base_url / key。"""
    site = await _make_site("SafeSite")
    await _make_score(site, "claude", composite_score=77)

    resp = await client.get("/rank?leaderboard=claude")
    body = resp.json()
    entry = body["main"][0]
    assert "base_url" not in entry
    assert "encrypted_key" not in entry
    assert "key_hint" not in entry
    assert "owner_id" not in entry
    assert "safesite.example" not in resp.text


async def test_invalid_leaderboard_422(client):
    """未知分榜返回 422。"""
    resp = await client.get("/rank?leaderboard=grok")
    assert resp.status_code == 422


async def test_invalid_sort_422(client):
    """未知排序键返回 422。"""
    resp = await client.get("/rank?leaderboard=claude&sort=price")
    assert resp.status_code == 422


async def test_empty_leaderboard_ok(client):
    """无数据时返回空主榜/观察区，不报错。"""
    resp = await client.get("/rank?leaderboard=claude")
    assert resp.status_code == 200
    body = resp.json()
    assert body["main"] == []
    assert body["observing"] == []
