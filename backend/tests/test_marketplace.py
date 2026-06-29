"""中转集市测试：发帖、筛选、关帖、对接 pending→confirmed、换名片、权限墙、履历附着。"""


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


async def _register_user(client, email: str):
    """注册普通用户（非站长），返回 headers。"""
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": "user"},
    )
    assert resp.status_code == 201
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _login_admin(client, email: str = "m_admin@test.com"):
    """直接造一个 admin 用户并登录，返回 headers。"""
    from app.core.security import hash_password
    from app.models.user import User

    await User.create(email=email, password_hash=hash_password("adminpass1"), role="admin")
    resp = await client.post("/auth/login", json={"email": email, "password": "adminpass1"})
    assert resp.status_code == 200
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _post_body(**over):
    body = {
        "post_type": "supply",
        "direction": "upstream",
        "model_family": "claude",
        "rate": "0.05",
        "rpm": 200,
        "volume": "日均 100w",
        "settlement": "weekly",
        "note": "claude 上游放量",
    }
    body.update(over)
    return body


async def test_create_post(client):
    """站长发帖成功，返回结构化字段 + 自己的履历名片。"""
    headers, _ = await _register_owner(client, "m_owner1@example.com")
    resp = await client.post("/market/posts", headers=headers, json=_post_body())
    assert resp.status_code == 201
    body = resp.json()
    assert body["post_type"] == "supply"
    assert body["model_family"] == "claude"
    assert body["status"] == "open"
    assert body["is_mine"] is True
    assert "author_reputation" in body


async def test_create_post_invalid_enum_422(client):
    """枚举非法返回 422。"""
    headers, _ = await _register_owner(client, "m_owner2@example.com")
    resp = await client.post(
        "/market/posts", headers=headers, json=_post_body(model_family="llama")
    )
    assert resp.status_code == 422


async def test_market_requires_owner(client):
    """普通用户进集市被拦（403）；未登录 401。"""
    user_headers = await _register_user(client, "m_user@example.com")
    assert (await client.get("/market/posts", headers=user_headers)).status_code == 403
    assert (await client.get("/market/posts")).status_code == 401


async def test_list_and_filter_posts(client):
    """按模型族 / 类型筛选；默认只列 open。"""
    headers, _ = await _register_owner(client, "m_owner3@example.com")
    await client.post("/market/posts", headers=headers, json=_post_body(model_family="claude"))
    await client.post("/market/posts", headers=headers, json=_post_body(model_family="gpt"))
    await client.post(
        "/market/posts", headers=headers, json=_post_body(post_type="demand", model_family="claude")
    )

    # 全部 open
    allp = await client.get("/market/posts", headers=headers)
    assert len(allp.json()) == 3
    # 只看 claude
    claude = await client.get("/market/posts?model_family=claude", headers=headers)
    assert len(claude.json()) == 2
    # claude 且 supply
    supply = await client.get(
        "/market/posts?model_family=claude&post_type=supply", headers=headers
    )
    assert len(supply.json()) == 1


async def test_filter_by_max_rate(client):
    """max_rate 过滤倍率 ≤ X。"""
    headers, _ = await _register_owner(client, "m_owner4@example.com")
    await client.post("/market/posts", headers=headers, json=_post_body(rate="0.05"))
    await client.post("/market/posts", headers=headers, json=_post_body(rate="0.20"))

    resp = await client.get("/market/posts?max_rate=0.10", headers=headers)
    rates = [float(p["rate"]) for p in resp.json()]
    assert rates == [0.05]


async def test_close_post(client):
    """发帖人关帖后，默认列表不再出现。"""
    headers, _ = await _register_owner(client, "m_owner5@example.com")
    post = (await client.post("/market/posts", headers=headers, json=_post_body())).json()
    close = await client.post(f"/market/posts/{post['post_id']}/close", headers=headers)
    assert close.status_code == 200
    assert close.json()["status"] == "closed"
    assert len((await client.get("/market/posts", headers=headers)).json()) == 0


async def test_cannot_close_others_post(client):
    """非发帖人关帖返回 403。"""
    h1, _ = await _register_owner(client, "m_owner6@example.com")
    h2, _ = await _register_owner(client, "m_owner7@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    resp = await client.post(f"/market/posts/{post['post_id']}/close", headers=h2)
    assert resp.status_code == 403


async def test_cannot_respond_own_post(client):
    """不能对接自己的帖子（400）。"""
    headers, _ = await _register_owner(client, "m_owner8@example.com")
    post = (await client.post("/market/posts", headers=headers, json=_post_body())).json()
    resp = await client.post(f"/market/posts/{post['post_id']}/respond", headers=headers)
    assert resp.status_code == 400


async def test_respond_pending_no_contact(client):
    """对接发起后 pending，未确认前不交换名片。"""
    h1, _ = await _register_owner(client, "m_author1@example.com")
    h2, _ = await _register_owner(client, "m_responder1@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()

    resp = await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "pending"
    assert body["contact"] is None


async def test_confirm_exchanges_contact_cards(client):
    """发帖人确认后双方互见名片：发起人在「我的对接」看到发帖人名片，发帖人在「收到的对接」看到发起人名片。"""
    h1, author_id = await _register_owner(
        client, "m_author2@example.com", wechat="wx_author", qq="22222"
    )
    h2, responder_id = await _register_owner(
        client, "m_responder2@example.com", wechat="wx_responder", qq="33333"
    )
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    resp = (await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)).json()

    # 发帖人确认
    confirm = await client.post(f"/market/responses/{resp['response_id']}/confirm", headers=h1)
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"

    # 发起人「我的对接」：见发帖人名片
    mine = await client.get("/market/responses/mine", headers=h2)
    card = mine.json()[0]["contact"]
    assert card is not None
    assert card["wechat"] == "wx_author"
    assert card["user_id"] == author_id

    # 发帖人「收到的对接」：见发起人名片
    incoming = await client.get("/market/responses/incoming", headers=h1)
    card2 = incoming.json()[0]["contact"]
    assert card2 is not None
    assert card2["wechat"] == "wx_responder"
    assert card2["user_id"] == responder_id


async def test_only_post_owner_can_confirm(client):
    """非发帖人确认对接返回 403。"""
    h1, _ = await _register_owner(client, "m_author3@example.com")
    h2, _ = await _register_owner(client, "m_responder3@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    resp = (await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)).json()
    # 发起人自己确认（无权）
    bad = await client.post(f"/market/responses/{resp['response_id']}/confirm", headers=h2)
    assert bad.status_code == 403


async def test_cannot_respond_closed_post(client):
    """已关闭帖不能对接（409）。"""
    h1, _ = await _register_owner(client, "m_author4@example.com")
    h2, _ = await _register_owner(client, "m_responder4@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    await client.post(f"/market/posts/{post['post_id']}/close", headers=h1)
    resp = await client.post(f"/market/posts/{post['post_id']}/respond", headers=h2)
    assert resp.status_code == 409


async def test_admin_can_browse_posts(client):
    """管理员可浏览集市帖子（监管视角），帖子 is_mine 恒为 False。"""
    h1, _ = await _register_owner(client, "m_admin_browse_owner@example.com")
    await client.post("/market/posts", headers=h1, json=_post_body())
    admin = await _login_admin(client, "m_admin1@test.com")

    resp = await client.get("/market/posts", headers=admin)
    assert resp.status_code == 200
    posts = resp.json()
    assert len(posts) == 1
    assert posts[0]["is_mine"] is False


async def test_admin_can_close_any_post(client):
    """管理员可关闭任意站长的帖子（内容下架）。"""
    h1, _ = await _register_owner(client, "m_admin_close_owner@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    admin = await _login_admin(client, "m_admin2@test.com")

    resp = await client.post(f"/market/posts/{post['post_id']}/close", headers=admin)
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


async def test_admin_cannot_create_post(client):
    """管理员不能发帖（发帖是站长交易动作，403）。"""
    admin = await _login_admin(client, "m_admin3@test.com")
    resp = await client.post("/market/posts", headers=admin, json=_post_body())
    assert resp.status_code == 403


async def test_admin_cannot_respond(client):
    """管理员不能对接（对接是站长交易动作，403）。"""
    h1, _ = await _register_owner(client, "m_admin_resp_owner@example.com")
    post = (await client.post("/market/posts", headers=h1, json=_post_body())).json()
    admin = await _login_admin(client, "m_admin4@test.com")

    resp = await client.post(f"/market/posts/{post['post_id']}/respond", headers=admin)
    assert resp.status_code == 403


async def test_plain_user_still_blocked_from_browse(client):
    """普通用户仍不能浏览集市（仅站长/管理员）。"""
    user = await _register_user(client, "m_plain_user@example.com")
    resp = await client.get("/market/posts", headers=user)
    assert resp.status_code == 403
