"""认证接口测试：注册 → 登录 → /auth/me 闭环，含主要失败用例。"""


async def test_register_and_me(client):
    """注册成功返回令牌，用令牌可取到当前用户信息。"""
    resp = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "password123"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == "alice@example.com"
    assert body["user"]["role"] == "user"
    # 响应绝不含敏感字段
    assert "password" not in body["user"]
    assert "password_hash" not in body["user"]

    token = body["access_token"]
    me = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "alice@example.com"


async def test_register_duplicate_email(client):
    """同邮箱重复注册返回 409。"""
    payload = {"email": "dup@example.com", "password": "password123"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 409


async def test_owner_requires_contact(client):
    """站长注册缺少微信/QQ 应被 schema 校验拒绝（422）。"""
    resp = await client.post(
        "/auth/register",
        json={"email": "owner@example.com", "password": "password123", "role": "owner"},
    )
    assert resp.status_code == 422

    ok = await client.post(
        "/auth/register",
        json={
            "email": "owner2@example.com",
            "password": "password123",
            "role": "owner",
            "wechat": "wx_123",
            "qq": "100000",
        },
    )
    assert ok.status_code == 201
    assert ok.json()["user"]["role"] == "owner"


async def test_login_success_and_wrong_password(client):
    """正确密码登录成功；错误密码返回 401。"""
    await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "password": "password123"},
    )

    ok = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "password123"},
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    bad = await client.post(
        "/auth/login",
        json={"email": "bob@example.com", "password": "wrong-password"},
    )
    assert bad.status_code == 401


async def test_me_without_token(client):
    """未带令牌访问 /auth/me 返回 401。"""
    resp = await client.get("/auth/me")
    assert resp.status_code == 401


async def test_me_with_invalid_token(client):
    """伪造/损坏令牌返回 401。"""
    resp = await client.get("/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
