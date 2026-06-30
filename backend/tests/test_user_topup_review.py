"""C 端 user_topup 评价测试。"""

from app.models.relay_site import RelaySite
from app.models.review import Review
from app.models.site_score import SiteScore


async def _register_user(client, email: str):
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": "user"},
    )
    assert resp.status_code == 201
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["user_id"]


async def _make_site(slug="topup-site", status="online") -> RelaySite:
    return await RelaySite.create(
        owner_id="01980000-0000-7000-8000-000000000001",
        name="TopupSite",
        slug=slug,
        base_url="https://topup.example/v1",
        encrypted_key="ENC::x",
        key_hint="sk-***0000",
        status=status,
        declared_models=["gpt-4o"],
    )


async def test_user_topup_review_verified(monkeypatch, client):
    """用户 key 验证通过后写 user_topup + verified，并刷新 review_score。"""
    site = await _make_site()
    headers, user_id = await _register_user(client, "topup-user@example.com")

    async def fake_verify(self, *, base_url: str, api_key: str) -> bool:
        assert base_url == "https://topup.example/v1"
        assert api_key == "sk-user-paid"
        return True

    monkeypatch.setattr(
        "app.services.topup_verifier.HttpTopupVerifier.verify",
        fake_verify,
    )

    resp = await client.post(
        "/sites/topup-site/reviews",
        headers=headers,
        json={"api_key": "sk-user-paid", "rating": 5, "content": "充值后可用"},
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["site_id"] == str(site.site_id)
    assert body["author_id"] == user_id
    assert body["review_type"] == "user_topup"
    assert body["verified"] is True

    saved = await Review.filter(site_id=site.site_id, review_type="user_topup").first()
    assert saved is not None
    score = await SiteScore.filter(site_id=site.site_id, leaderboard="gpt").first()
    assert score is not None
    assert score.review_score is not None


async def test_user_topup_review_verification_failed(monkeypatch, client):
    """无法证明充值/用量时拒绝评价，不写 reviews。"""
    await _make_site(slug="topup-denied")
    headers, _ = await _register_user(client, "topup-denied@example.com")

    async def fake_verify(self, *, base_url: str, api_key: str) -> bool:
        return False

    monkeypatch.setattr(
        "app.services.topup_verifier.HttpTopupVerifier.verify",
        fake_verify,
    )

    resp = await client.post(
        "/sites/topup-denied/reviews",
        headers=headers,
        json={"api_key": "sk-no-usage", "rating": 4},
    )

    assert resp.status_code == 403
    assert await Review.filter(review_type="user_topup").count() == 0


async def test_user_topup_review_cannot_duplicate(monkeypatch, client):
    """同一用户对同一站点只能提交一条 C 端评价。"""
    await _make_site(slug="topup-duplicate")
    headers, _ = await _register_user(client, "topup-duplicate@example.com")

    async def fake_verify(self, *, base_url: str, api_key: str) -> bool:
        return True

    monkeypatch.setattr(
        "app.services.topup_verifier.HttpTopupVerifier.verify",
        fake_verify,
    )

    first = await client.post(
        "/sites/topup-duplicate/reviews",
        headers=headers,
        json={"api_key": "sk-paid-1", "rating": 5},
    )
    assert first.status_code == 201

    again = await client.post(
        "/sites/topup-duplicate/reviews",
        headers=headers,
        json={"api_key": "sk-paid-2", "rating": 1},
    )
    assert again.status_code == 409


async def test_user_topup_review_requires_login(client):
    """C 端评价必须登录；游客不能提交 key。"""
    await _make_site(slug="topup-login")

    resp = await client.post(
        "/sites/topup-login/reviews",
        json={"api_key": "sk-user-paid", "rating": 5},
    )

    assert resp.status_code == 401


async def test_user_topup_review_pending_site_404(monkeypatch, client):
    """pending/rejected 站点不开放评价。"""
    await _make_site(slug="topup-pending", status="pending")
    headers, _ = await _register_user(client, "topup-pending@example.com")

    resp = await client.post(
        "/sites/topup-pending/reviews",
        headers=headers,
        json={"api_key": "sk-user-paid", "rating": 5},
    )

    assert resp.status_code == 404
