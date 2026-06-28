"""健康检查接口测试。"""


async def test_health_ok(client):
    """/health 返回 200，status=ok，sqlite 内存库可达 db=up。"""
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["db"] == "up"
