"""探测编排：把 HTTP 探测 + 状态机 + 评分串成一轮。

替换原桩。每轮：拉站 → 并发探测 → 写 probe_results → 跑状态机落库
→ online→abnormal 瞬间插队质量探测 → 轮尾重算受影响站 scores + 各榜 rank。

红线：站长 key 只在本模块内 decrypt_key 后即时用于一次请求，绝不出函数、不进日志。
client 可注入（测试用 httpx.MockTransport），默认建真实 AsyncClient。
"""

import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from tortoise import timezone

from app.core.security import decrypt_key
from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.services.scoring import recompute_ranks, recompute_site_scores
from app.worker.http_probe import probe_alive, probe_quality
from app.worker.probe_stats import compute_stats
from app.worker.state_machine import decide_transition

logger = logging.getLogger("router_hub.worker")

# 一轮内并发探测上限，避免打爆本机出口与上游
_CONCURRENCY = 20

# 存活探测覆盖的状态：在线/异常/观察 + 坟场三态（坟场站仍探测以便复活）
_ALIVE_STATUSES = ["online", "abnormal", "observing", "revived", "suspected_dead", "dead"]
# 质量探测覆盖的状态：仅正式在主榜或观察的站（烧钱，坟场站不烧）
_QUALITY_STATUSES = ["online", "abnormal", "observing", "revived"]

# PLACEHOLDER_BODY


@asynccontextmanager
async def _default_client():
    """默认 HTTP 客户端（follow_redirects 让 base_url 带/不带尾斜杠都能用）。"""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        yield client


async def _apply_transition(site: RelaySite) -> bool:
    """按当前探测统计跑状态机；若需转移则落库。返回是否发生转移。"""
    stats = await compute_stats(site)
    new_status = decide_transition(site.status, stats)
    if new_status is None or new_status == site.status:
        return False
    old_status = site.status
    site.status = new_status
    site.status_changed_at = timezone.now()
    await site.save(update_fields=["status", "status_changed_at", "updated_at"])
    logger.info("[state] site=%s %s → %s", site.slug, old_status, new_status)
    return True


async def _record_alive(site: RelaySite, client: httpx.AsyncClient) -> ProbeResult:
    """对一个站做一次存活探测并落 probe_results，同时更新站点探测时间戳。

    带站长 key 探测（许多上游 /v1/models 需鉴权）；key 即时解密、用完即弃，绝不出本函数。
    """
    api_key = decrypt_key(site.encrypted_key) if site.encrypted_key else None
    outcome = await probe_alive(client, site.base_url, api_key)
    del api_key  # 用完即弃
    now = timezone.now()
    result = await ProbeResult.create(
        site_id=site.site_id,
        probe_type="alive",
        probed_at=now,
        ttfb_ms=outcome.ttfb_ms,
        total_ms=outcome.total_ms,
        http_status=outcome.http_status,
        is_alive=outcome.is_alive,
        error_sample=outcome.error_sample,
    )
    site.last_probe_at = now
    if outcome.is_alive and site.first_seen_at is None:
        site.first_seen_at = now
        await site.save(update_fields=["last_probe_at", "first_seen_at", "updated_at"])
    else:
        await site.save(update_fields=["last_probe_at", "updated_at"])
    return result


async def _record_quality(site: RelaySite, client: httpx.AsyncClient) -> ProbeResult | None:
    """用站长 key 做一次质量探测并落库；无可探测模型则跳过。

    key 仅在此解密、即时用于一次请求，绝不出本函数。
    """
    models = site.declared_models or []
    if not models:
        return None
    model = models[0]  # MVP：取声明的第一个模型探测
    api_key = decrypt_key(site.encrypted_key)
    outcome = await probe_quality(client, site.base_url, api_key, model)
    del api_key  # 用完即弃
    now = timezone.now()
    return await ProbeResult.create(
        site_id=site.site_id,
        probe_type="quality",
        probed_at=now,
        target_model=outcome.target_model,
        ttfb_ms=outcome.ttfb_ms,
        total_ms=outcome.total_ms,
        http_status=outcome.http_status,
        is_alive=outcome.is_alive,
        is_authentic=outcome.is_authentic,
        error_sample=outcome.error_sample,
    )


async def run_alive_probe(client: httpx.AsyncClient | None = None) -> None:
    """存活探测轮：并发打 /v1/models，写结果，跑状态机，轮尾重算分。"""
    if client is None:
        async with _default_client() as c:
            await run_alive_probe(c)
        return

    sites = await RelaySite.filter(status__in=_ALIVE_STATUSES)
    if not sites:
        logger.info("[alive] 无可探测站点")
        return

    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _one(site: RelaySite) -> None:
        async with sem:
            prev_status = site.status
            await _record_alive(site, client)
            transitioned = await _apply_transition(site)
            # online→abnormal 瞬间插队一次质量探测，分辨整站挂了 vs /v1/models 抽风
            if transitioned and prev_status == "online" and site.status == "abnormal":
                await _record_triggered_quality(site, client)
            await recompute_site_scores(site)

    await asyncio.gather(*(_one(s) for s in sites))
    await _recompute_all_ranks()
    logger.info("[alive] 完成 %d 站", len(sites))


async def run_quality_probe(client: httpx.AsyncClient | None = None) -> None:
    """质量探测轮：用站长 key 打 /v1/chat 测 TTFB/真实性，写结果，重算分。"""
    if client is None:
        async with _default_client() as c:
            await run_quality_probe(c)
        return

    sites = await RelaySite.filter(status__in=_QUALITY_STATUSES)
    sem = asyncio.Semaphore(_CONCURRENCY)

    async def _one(site: RelaySite) -> None:
        async with sem:
            # TODO(budget): probe_budget_daily>0 时按当日已用质量探测数扣减/降频；
            #   MVP 视 budget_daily=0 为不限。
            result = await _record_quality(site, client)
            if result is not None:
                await recompute_site_scores(site)

    await asyncio.gather(*(_one(s) for s in sites))
    await _recompute_all_ranks()
    logger.info("[quality] 完成 %d 站", len(sites))


async def _record_triggered_quality(site: RelaySite, client: httpx.AsyncClient) -> None:
    """触发探测：把一次质量探测标为 triggered 落库（online→abnormal 瞬间插队）。"""
    models = site.declared_models or []
    if not models:
        return
    api_key = decrypt_key(site.encrypted_key)
    outcome = await probe_quality(client, site.base_url, api_key, models[0])
    del api_key
    await ProbeResult.create(
        site_id=site.site_id,
        probe_type="triggered",
        probed_at=timezone.now(),
        target_model=outcome.target_model,
        ttfb_ms=outcome.ttfb_ms,
        total_ms=outcome.total_ms,
        http_status=outcome.http_status,
        is_alive=outcome.is_alive,
        is_authentic=outcome.is_authentic,
        error_sample=outcome.error_sample,
    )


async def run_triggered_probe(site_id: str, client: httpx.AsyncClient | None = None) -> None:
    """对单站插队一次触发探测（供外部异常路径调用）。"""
    if client is None:
        async with _default_client() as c:
            await run_triggered_probe(site_id, c)
        return
    site = await RelaySite.filter(site_id=site_id).first()
    if site is None:
        return
    await _record_triggered_quality(site, client)
    await recompute_site_scores(site)
    await _recompute_all_ranks()


async def _recompute_all_ranks() -> None:
    """三榜名次统一重算。"""
    for board in ("claude", "gpt", "gemini"):
        await recompute_ranks(board)
