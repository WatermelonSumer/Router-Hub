"""探测计数器：从 probe_results 算状态机所需的统计（不加列、不碰判定）。

blueprint 原则：判定只依赖实际探测到的事实，worker 自身宕机不污染判定。
维护窗内的失败按红线剔除（不计入连续失败计数器、不计入在线率分母）。
"""

from datetime import datetime

from tortoise import timezone

from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.worker.state_machine import ProbeStats

# 算连续成败时回看的最近探测条数上限（足够覆盖最长阈值 FAIL_TO_DEAD=576）
_LOOKBACK = 800


def _in_maintenance_window(when: datetime, windows: list | None) -> bool:
    """判断某时刻是否落在站长声明的维护窗内。

    windows 形如 [{"start": ISO8601, "end": ISO8601}, ...]；格式异常一律按「不在窗内」
    处理（宁可计入失败，也不让坏数据放过真跑路）。
    """
    if not windows:
        return False
    for w in windows:
        try:
            start = datetime.fromisoformat(w["start"])
            end = datetime.fromisoformat(w["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if start <= when <= end:
            return True
    return False


async def _recent_alive_results(site: RelaySite) -> list[ProbeResult]:
    """取该站最近的存活相关探测（alive + triggered），按时间倒序，已剔除维护窗失败。"""
    rows = (
        await ProbeResult.filter(site_id=site.site_id, probe_type__in=["alive", "triggered"])
        .order_by("-probed_at")
        .limit(_LOOKBACK)
    )
    windows = site.maintenance_windows
    # 维护窗内的「失败」整条剔除（不参与连续计数）；窗内成功仍保留
    return [r for r in rows if r.is_alive or not _in_maintenance_window(r.probed_at, windows)]


def _consecutive(results: list[ProbeResult], *, want_alive: bool) -> int:
    """从最近一条往回数，连续满足 is_alive==want_alive 的条数。"""
    n = 0
    for r in results:
        if r.is_alive == want_alive:
            n += 1
        else:
            break
    return n


async def compute_stats(site: RelaySite) -> ProbeStats:
    """汇总某站当前的探测统计，供状态机判定。"""
    results = await _recent_alive_results(site)
    consecutive_fails = _consecutive(results, want_alive=False)
    consecutive_successes = _consecutive(results, want_alive=True)

    # 在当前状态停留的天数：以 status_changed_at 为准，缺失则退回 first_seen_at/created_at
    anchor = site.status_changed_at or site.first_seen_at or site.created_at
    days_in_status = 0.0
    if anchor is not None:
        days_in_status = (timezone.now() - anchor).total_seconds() / 86400.0

    # observing 毕业样本数：进入当前状态后累计的 alive / quality 探测条数
    alive_count = 0
    quality_count = 0
    if site.status == "observing" and anchor is not None:
        alive_count = await ProbeResult.filter(
            site_id=site.site_id,
            probe_type__in=["alive", "triggered"],
            probed_at__gte=anchor,
        ).count()
        quality_count = await ProbeResult.filter(
            site_id=site.site_id,
            probe_type="quality",
            probed_at__gte=anchor,
        ).count()

    return ProbeStats(
        consecutive_fails=consecutive_fails,
        consecutive_successes=consecutive_successes,
        days_in_status=days_in_status,
        alive_probe_count=alive_count,
        quality_probe_count=quality_count,
    )
