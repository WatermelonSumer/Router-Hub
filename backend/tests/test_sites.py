"""中转站上架接口测试：站长上架、key 不外泄、slug 查重、权限校验。"""


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
