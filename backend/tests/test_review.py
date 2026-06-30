"""B 端站长互评测试（owner_deal）。

覆盖：confirmed 对接双方可评帖子绑定站点、写 owner_deal+verified、刷 review_score；
非对接方 403、pending 未确认 409、帖子无绑定站点 400、重复评 409、rating 越界 422。
"""

from app.models.relay_site import RelaySite
from app.models.review import Review
from app.models.site_score import SiteScore


async def _register_owner(client, email: str, wechat="wx_x", qq="10001"):
    """注册站长，返回 (headers, user_id)。"""
    resp = await client.post(
        "/auth/register",
        json={
            "email": email,
            "password": "password123",
            "role": "owner",
            "wechat": wechat,
            "qq": qq,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["user_id"]


async def _make_site(owner_id: str, slug: str, name="DealSite") -> RelaySite:
    """给某站长造一个站点（互评对象）。"""
    return await RelaySite.create(
        owner_id=owner_id,
        name=name,
        slug=slug,
        base_url="https://deal.example/v1",
        encrypted_key="ENC::x",
        key_hint="sk-***0000",
        status="online",
        declared_models=["claude-3-5-sonnet"],
    )


def _post_body(**over):
    body = {
        "post_type": "supply",
        "direction": "upstream",
        "model_family": "claude",
        "rate": "0.05",
    }
    body.update(over)
    return body


async def _confirmed_deal(client):
    """造一对站长 + 各自站点 + 一条 confirmed 对接。

    返回 (h_author, h_responder, response_id, author_site)。
    """
    h1, a_id = await _register_owner(client, "rv_author@example.com", wechat="wx_a")
    h2, r_id = await _register_owner(client, "rv_responder@example.com", wechat="wx_b")
    author_site = await _make_site(a_id, "author-site")
    await _make_site(r_id, "responder-site")

    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    assert post["site_id"] is not None  # 发帖自动绑定作者站点
    resp = (await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)).json()
    await client.post(f"/market/responses/{resp['response_id']}/confirm", headers=h1)
    return h1, h2, resp["response_id"], author_site


async def test_post_binds_author_site(client):
    """发帖自动绑定发帖人名下站点，PostView 含 site_id/site_name。"""
    h1, a_id = await _register_owner(client, "rv_bind@example.com")
    await _make_site(a_id, "bind-site", name="BindSite")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    assert post["site_id"] is not None
    assert post["site_name"] == "BindSite"
    assert post["site_slug"] == "bind-site"


async def test_both_parties_can_review(client):
    """confirmed 对接双方都能评帖子绑定的站点，写 owner_deal + verified。"""
    h1, h2, response_id, author_site = await _confirmed_deal(client)

    # 对接发起人评价
    r2 = await client.post(
        f"/market/responses/{response_id}/review",
        headers=h2,
        json={"rating": 5, "content": "靠谱上游"},
    )
    assert r2.status_code == 201
    body = r2.json()
    assert body["review_type"] == "owner_deal"
    assert body["verified"] is True
    assert body["rating"] == 5
    assert body["site_id"] == str(author_site.site_id)

    # 发帖人也能评（同一站点，但作者不同，不算重复）
    r1 = await client.post(
        f"/market/responses/{response_id}/review", headers=h1, json={"rating": 4}
    )
    assert r1.status_code == 201

    # reviews 表落了两条 owner_deal
    count = await Review.filter(site_id=author_site.site_id, review_type="owner_deal").count()
    assert count == 2


async def test_review_refreshes_score(client):
    """互评后刷新该站 review_score（owner_deal verified 计入加权）。"""
    h1, h2, response_id, author_site = await _confirmed_deal(client)
    await client.post(f"/market/responses/{response_id}/review", headers=h2, json={"rating": 5})
    score = await SiteScore.filter(site_id=author_site.site_id, leaderboard="claude").first()
    assert score is not None
    assert score.review_score is not None


async def test_cannot_review_pending(client):
    """对接未确认（pending）不能评价，返回 409。"""
    h1, a_id = await _register_owner(client, "rv_p_author@example.com")
    h2, r_id = await _register_owner(client, "rv_p_responder@example.com")
    await _make_site(a_id, "p-author-site")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    resp = (await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)).json()
    # 不 confirm，直接评
    r = await client.post(
        f"/market/responses/{resp['response_id']}/review", headers=h2, json={"rating": 5}
    )
    assert r.status_code == 409


async def test_non_party_cannot_review(client):
    """非对接两方不能评价，返回 403。"""
    h1, h2, response_id, _ = await _confirmed_deal(client)
    h3, _ = await _register_owner(client, "rv_outsider@example.com")
    r = await client.post(f"/market/responses/{response_id}/review", headers=h3, json={"rating": 1})
    assert r.status_code == 403


async def test_cannot_review_twice(client):
    """同一作者对同一站点重复评价，返回 409。"""
    h1, h2, response_id, _ = await _confirmed_deal(client)
    first = await client.post(
        f"/market/responses/{response_id}/review", headers=h2, json={"rating": 5}
    )
    assert first.status_code == 201
    again = await client.post(
        f"/market/responses/{response_id}/review", headers=h2, json={"rating": 1}
    )
    assert again.status_code == 409


async def test_rating_out_of_range_422(client):
    """rating 越界返回 422。"""
    h1, h2, response_id, _ = await _confirmed_deal(client)
    r = await client.post(f"/market/responses/{response_id}/review", headers=h2, json={"rating": 6})
    assert r.status_code == 422


async def test_no_site_no_review(client):
    """帖子未绑定站点（发帖人无站点）时不能评价，返回 400。"""
    # 发帖人无站点 → 帖子 site_id 为空
    h1, _ = await _register_owner(client, "rv_nosite_author@example.com")
    h2, r_id = await _register_owner(client, "rv_nosite_responder@example.com")
    await _make_site(r_id, "ns-responder-site")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    assert post["site_id"] is None
    resp = (await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)).json()
    await client.post(f"/market/responses/{resp['response_id']}/confirm", headers=h1)
    r = await client.post(
        f"/market/responses/{resp['response_id']}/review", headers=h2, json={"rating": 5}
    )
    assert r.status_code == 400
