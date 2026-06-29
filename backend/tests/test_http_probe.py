"""HTTP 探测层测试：用 httpx.MockTransport 模拟上游，不发真实网络请求。"""

import httpx

from app.worker.http_probe import probe_alive, probe_quality


def _client(handler) -> httpx.AsyncClient:
    """构造走 MockTransport 的客户端。"""
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_probe_alive_ok():
    """/v1/models 返回 200 → 存活，带 TTFB。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/models")
        return httpx.Response(200, json={"data": []})

    async with _client(handler) as c:
        out = await probe_alive(c, "https://api.demo.test/v1")
    assert out.is_alive is True
    assert out.http_status == 200
    assert out.ttfb_ms is not None


async def test_probe_alive_with_key_sends_auth():
    """带 key 的存活探测：发送 Authorization 头，且 key 不进结果。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/v1/models")
        assert request.headers["Authorization"] == "Bearer sk-alive-key"
        return httpx.Response(200, json={"data": [{"id": "gpt-4o"}]})

    async with _client(handler) as c:
        out = await probe_alive(c, "https://api.demo.test", "sk-alive-key")
    assert out.is_alive is True
    assert out.http_status == 200
    # 红线：key 绝不出现在结果任何字段
    assert "sk-alive-key" not in str(out)


async def test_probe_alive_non_2xx():
    """非 2xx → 未存活。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="bad gateway")

    async with _client(handler) as c:
        out = await probe_alive(c, "https://api.demo.test/v1")
    assert out.is_alive is False
    assert out.http_status == 502


async def test_probe_alive_timeout():
    """超时 → 未存活，error_sample 标超时。"""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async with _client(handler) as c:
        out = await probe_alive(c, "https://api.demo.test/v1")
    assert out.is_alive is False
    assert out.error_sample == "超时"


async def test_probe_quality_authentic():
    """chat 返回有内容的 choice → authentic，key 不进结果。"""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-secret-key"
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    async with _client(handler) as c:
        out = await probe_quality(c, "https://api.demo.test/v1", "sk-secret-key", "gpt-4o")
    assert out.is_alive is True
    assert out.is_authentic is True
    assert out.target_model == "gpt-4o"
    # 红线：key 绝不出现在结果任何字段
    assert "sk-secret-key" not in str(out)


async def test_probe_quality_empty_choices_not_authentic():
    """返回空 choices（假模型/空壳）→ 不通过真实性。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    async with _client(handler) as c:
        out = await probe_quality(c, "https://api.demo.test/v1", "sk-x", "claude-3-5-sonnet")
    assert out.is_alive is True
    assert out.is_authentic is False


async def test_probe_quality_non_2xx():
    """chat 非 2xx → 未存活、不真实。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "unauthorized"})

    async with _client(handler) as c:
        out = await probe_quality(c, "https://api.demo.test/v1", "sk-x", "gpt-4o")
    assert out.is_alive is False
    assert out.is_authentic is False
    assert out.http_status == 401
