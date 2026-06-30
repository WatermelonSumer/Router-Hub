"""站点详情读取业务逻辑（C 端详情页）。

只读 relay_sites / probe_results / site_scores，绝不在此算综合分（那是 worker 的活）。
在线率曲线复用 probe_stats 的维护窗剔除红线：窗内失败不计入分母。

红线：返回的数据载体绝不携带 base_url / encrypted_key / key_hint。
"""

from collections import defaultdict
from datetime import date, timedelta

from tortoise import timezone

from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore
from app.worker.probe_stats import _in_maintenance_window

# 详情页可公开的站点状态（pending/rejected 不对外，避免未审核站点被收录）
_PUBLIC_STATUSES = (
    "observing",
    "online",
    "abnormal",
    "revived",
    "suspected_dead",
    "dead",
)


class SiteDetailNotFound(Exception):
    """目标站点不存在、已假删除，或尚不可公开（pending/rejected）。"""


def _percentile(values: list[int], pct: float) -> int | None:
    """取已排序无关的分位值（最近秩方法）；空列表返回 None。"""
    if not values:
        return None
    ordered = sorted(values)
    # 最近秩：ceil(pct/100 * n) - 1，clamp 到 [0, n-1]
    k = max(0, min(len(ordered) - 1, round(pct / 100 * len(ordered)) - 1))
    return ordered[k]


async def _public_site(slug: str) -> RelaySite:
    """按 slug 取可公开的站点，否则抛 SiteDetailNotFound。"""
    site = await RelaySite.filter(slug=slug).first()
    if site is None or site.status not in _PUBLIC_STATUSES:
        raise SiteDetailNotFound(slug)
    return site


async def compute_uptime_history(
    site: RelaySite, *, days: int = 30
) -> tuple[list[tuple[str, float | None]], float | None]:
    """算近 days 天逐日在线率曲线 + 总在线率。

    数据源：alive + triggered 探测。维护窗内的失败整条剔除（红线，与状态机一致）：
    既不计入当天分母，也不计入总在线率分母；窗内成功仍保留。
    某天无有效样本 → 当天 uptime 记 None（前端断点，不画成 0）。
    """
    now = timezone.now()
    since = now - timedelta(days=days)
    rows = await ProbeResult.filter(
        site_id=site.site_id,
        probe_type__in=["alive", "triggered"],
        probed_at__gte=since,
    ).order_by("probed_at")

    windows = site.maintenance_windows
    # 逐日分桶：date -> [total, alive]
    buckets: dict[date, list[int]] = defaultdict(lambda: [0, 0])
    grand_total = 0
    grand_alive = 0
    for r in rows:
        # 维护窗内的失败整条剔除，不进任何分母
        if not r.is_alive and _in_maintenance_window(r.probed_at, windows):
            continue
        day = r.probed_at.date()
        buckets[day][0] += 1
        grand_total += 1
        if r.is_alive:
            buckets[day][1] += 1
            grand_alive += 1

    # 输出连续 days 天（含无样本的天，uptime=None），按日期升序
    start_day = (now - timedelta(days=days - 1)).date()
    history: list[tuple[str, float | None]] = []
    for i in range(days):
        d = start_day + timedelta(days=i)
        total, alive = buckets.get(d, [0, 0])
        pct = round(alive / total * 100, 1) if total else None
        history.append((d.isoformat(), pct))

    overall = round(grand_alive / grand_total * 100, 1) if grand_total else None
    return history, overall


async def get_public_detail(slug: str) -> "PublicDetailData":
    """组装游客可见的详情数据（SSR 用）。站点不可公开则抛 SiteDetailNotFound。"""
    site = await _public_site(slug)

    history, uptime_30d = await compute_uptime_history(site)

    # 已验证可用：是否有过成功的质量探测（真打通 chat 拿到合理回复）
    verified = await ProbeResult.filter(
        site_id=site.site_id, probe_type="quality", is_authentic=True
    ).exists()

    scores = await SiteScore.filter(site_id=site.site_id)

    return PublicDetailData(
        site=site,
        uptime_history=history,
        uptime_30d=uptime_30d,
        verified=verified,
        scores=list(scores),
    )


async def get_gated_detail(slug: str) -> "GatedDetailData":
    """组装登录可见的硬信息（决策区 + 实测延迟）。不可公开则抛 SiteDetailNotFound。"""
    site = await _public_site(slug)

    # 从质量探测取 TTFB 分位（仅成功且有 ttfb 的样本）
    rows = await ProbeResult.filter(
        site_id=site.site_id, probe_type="quality", is_alive=True
    ).values_list("ttfb_ms", flat=True)
    ttfbs = [t for t in rows if t is not None]

    return GatedDetailData(
        site=site,
        ttfb_p50_ms=_percentile(ttfbs, 50),
        ttfb_p90_ms=_percentile(ttfbs, 90),
        latency_samples=len(ttfbs),
    )


class PublicDetailData:
    """游客详情数据载体；route 层转 SitePublicView。绝不暴露 key/base_url。"""

    def __init__(
        self,
        *,
        site: RelaySite,
        uptime_history: list[tuple[str, float | None]],
        uptime_30d: float | None,
        verified: bool,
        scores: list[SiteScore],
    ):
        self.site = site
        self.uptime_history = uptime_history
        self.uptime_30d = uptime_30d
        self.verified = verified
        self.scores = scores


class GatedDetailData:
    """登录详情数据载体；route 层转 SiteGatedView。绝不暴露 key/base_url。"""

    def __init__(
        self,
        *,
        site: RelaySite,
        ttfb_p50_ms: int | None,
        ttfb_p90_ms: int | None,
        latency_samples: int,
    ):
        self.site = site
        self.ttfb_p50_ms = ttfb_p50_ms
        self.ttfb_p90_ms = ttfb_p90_ms
        self.latency_samples = latency_samples
