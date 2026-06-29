"""整轮探测测试：sqlite + 注入 httpx.MockTransport，端到端跑 worker 一轮。

验证 probe_results 落库、状态机流转、site_scores 刷新，全程不发真实网络请求。
"""

from datetime import timedelta

import httpx
import pytest_asyncio
from tortoise import timezone

from app.core.security import encrypt_key, mask_key
from app.models.leaderboard_weight import LeaderboardWeight
from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore
from app.worker.probes import run_alive_probe, run_quality_probe


@pytest_asyncio.fixture
async def weights():
    """三榜权重（评分需要）。"""
    await LeaderboardWeight.create(
        leaderboard="gpt", w_uptime=0.4, w_speed=0.25, w_authenticity=0.25, w_review=0.1
    )


async def _make_site(status="online", days_ago_status=0.0) -> RelaySite:
    return await RelaySite.create(
        owner_id="00000000-0000-0000-0000-0000000000de",
        name="ProbeMe",
        slug="probe-me",
        base_url="https://api.probeme.test/v1",
        site_url="https://probeme.test",
        encrypted_key=encrypt_key("sk-owner-key-123"),
        key_hint=mask_key("sk-owner-key-123"),
        declared_models=["gpt-4o"],
        status=status,
        status_changed_at=timezone.now() - timedelta(days=days_ago_status),
    )


def _ok_client() -> httpx.AsyncClient:
    """全部探测都成功的客户端。"""

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/models"):
            return httpx.Response(200, json={"data": [{"id": "gpt-4o"}]})
        return httpx.Response(
            200, json={"choices": [{"message": {"role": "assistant", "content": "ok"}}]}
        )

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


def _down_client() -> httpx.AsyncClient:
    """全部探测都失败（502）的客户端。"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text="down")

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def test_alive_round_writes_probe_result(client, weights):
    """一轮存活探测后落 probe_results 且 is_alive=True。"""
    site = await _make_site()
    async with _ok_client() as c:
        await run_alive_probe(c)
    rows = await ProbeResult.filter(site_id=site.site_id, probe_type="alive")
    assert len(rows) == 1
    assert rows[0].is_alive is True


async def test_alive_round_recomputes_scores(client, weights):
    """存活探测后 site_scores 出现 uptime 分。"""
    site = await _make_site()
    async with _ok_client() as c:
        await run_alive_probe(c)
    score = await SiteScore.filter(site_id=site.site_id, leaderboard="gpt").first()
    assert score is not None
    assert score.uptime_score is not None


async def test_online_to_abnormal_after_failures(client, weights):
    """online 站连续失败达阈值后被状态机降为 abnormal。"""
    from app.core.config import settings

    site = await _make_site(status="online")
    async with _down_client() as c:
        for _ in range(settings.PROBE_FAIL_TO_ABNORMAL):
            await run_alive_probe(c)
    refreshed = await RelaySite.filter(site_id=site.site_id).first()
    assert refreshed.status == "abnormal"


async def test_quality_round_writes_authentic(client, weights):
    """质量探测落库且 is_authentic=True；key 不进 error_sample。"""
    site = await _make_site()
    async with _ok_client() as c:
        await run_quality_probe(c)
    rows = await ProbeResult.filter(site_id=site.site_id, probe_type="quality")
    assert len(rows) == 1
    assert rows[0].is_authentic is True
    assert rows[0].is_alive is True
    assert "sk-owner-key-123" not in (rows[0].error_sample or "")


async def test_quality_round_computes_speed_authenticity(client, weights):
    """质量探测后 site_scores 出现 speed/authenticity 分。"""
    site = await _make_site()
    async with _ok_client() as c:
        await run_quality_probe(c)
    score = await SiteScore.filter(site_id=site.site_id, leaderboard="gpt").first()
    assert score.speed_score is not None
    assert score.authenticity_score is not None
