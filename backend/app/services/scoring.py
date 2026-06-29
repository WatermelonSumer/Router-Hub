"""评分：四指标归一化（各 0-100）+ 缺失数据动态权重合成。

算法照搬 blueprint 六之二。归一化函数为纯函数（输入探测数据，输出分数），
便于单测；recompute_site_scores 负责读 DB → 调纯函数 → upsert site_scores。

关键红线（陷阱 C）：某指标无数据时绝不给 0 分，记为 None；合成时把其权重
按比例摊给有数据的指标（动态权重重分配），保证冷启动公平。
"""

import math
from dataclasses import dataclass
from datetime import datetime

from tortoise import timezone

from app.core.config import settings
from app.models.leaderboard_weight import LeaderboardWeight
from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.review import Review
from app.models.site_score import SiteScore


@dataclass
class AliveSample:
    """存活探测样本（算 uptime 用）。"""

    probed_at: datetime
    is_alive: bool


@dataclass
class QualitySample:
    """质量探测样本（算 speed / authenticity 用）。"""

    ttfb_ms: int | None
    is_authentic: bool


def uptime_score(samples: list[AliveSample]) -> float | None:
    """① 在线率：时间衰减加权（半衰期默认 7 天），非简单比例。

    wᵢ = 0.5^(age_days / HALFLIFE)；uptime = Σ(wᵢ·resultᵢ)/Σ(wᵢ) ×100。
    无样本返回 None。
    """
    if not samples:
        return None
    now = timezone.now()
    halflife = settings.UPTIME_HALFLIFE_DAYS
    num = 0.0
    den = 0.0
    for s in samples:
        age_days = max(0.0, (now - s.probed_at).total_seconds() / 86400.0)
        w = 0.5 ** (age_days / halflife)
        den += w
        if s.is_alive:
            num += w
    if den == 0:
        return None
    return num / den * 100.0


def _percentile(values: list[float], p: float) -> float:
    """线性插值百分位（p∈[0,1]）。values 非空。"""
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
    idx = p * (len(ordered) - 1)
    lo = math.floor(idx)
    hi = math.ceil(idx)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] + (ordered[hi] - ordered[lo]) * (idx - lo)


def speed_score(samples: list[QualitySample]) -> float | None:
    """② 速度：成功样本 TTFB 的 P90 → 锚点分段映射（非均值、非线性）。

    无成功样本（无 TTFB 数据）返回 None。
    """
    ttfbs = [float(s.ttfb_ms) for s in samples if s.is_authentic and s.ttfb_ms is not None]
    if not ttfbs:
        return None
    p90 = _percentile(ttfbs, 0.90)

    anchors_ms = settings.speed_anchors_ms
    anchors_score = settings.speed_anchors_score
    # ≤首拐点 → 满分
    if p90 <= anchors_ms[0]:
        return anchors_score[0]
    # 拐点间线性插值
    for i in range(len(anchors_ms) - 1):
        if p90 <= anchors_ms[i + 1]:
            lo_ms, hi_ms = anchors_ms[i], anchors_ms[i + 1]
            lo_sc, hi_sc = anchors_score[i], anchors_score[i + 1]
            ratio = (p90 - lo_ms) / (hi_ms - lo_ms)
            return lo_sc + (hi_sc - lo_sc) * ratio
    # 超末拐点：在 [0, 末分数] 线性衰减到 0（这里简化为末分数线性外推到 2× 末拐点归零）
    last_ms = anchors_ms[-1]
    last_sc = anchors_score[-1]
    overshoot = (p90 - last_ms) / last_ms  # 每超出一个末拐点宽度
    score = last_sc * max(0.0, 1.0 - overshoot)
    return max(0.0, score)


def authenticity_score(samples: list[QualitySample]) -> float | None:
    """③ 真实性：最近 N 次质量探测中 is_authentic 比例 ×100（非单次）。

    无质量样本返回 None。
    """
    window = settings.AUTHENTICITY_WINDOW
    recent = samples[:window]  # 调用方传入时已按时间倒序
    if not recent:
        return None
    authentic = sum(1 for s in recent if s.is_authentic)
    return authentic / len(recent) * 100.0


def review_score(ratings: list[float], global_mean: float | None) -> float | None:
    """④ 评价：贝叶斯平均（评价少时被先验稀释）。

    review_raw = (C·m + Σr)/(C+n)；m=全站均星先验，C 置信常数。
    无评价返回 None。
    """
    if not ratings:
        return None
    n = len(ratings)
    c = settings.REVIEW_BAYESIAN_C
    m = global_mean if global_mean is not None else sum(ratings) / n
    raw = (c * m + sum(ratings)) / (c + n)
    return raw / 5.0 * 100.0


@dataclass
class Weights:
    """某分榜四指标权重。"""

    uptime: float
    speed: float
    authenticity: float
    review: float


def composite_score(
    *,
    uptime: float | None,
    speed: float | None,
    authenticity: float | None,
    review: float | None,
    weights: Weights,
) -> float | None:
    """⑤ 综合分 + 缺失数据动态权重：只对有数据的指标加权并归一化。

    composite = Σ(scoreᵢ·wᵢ for i∈有数据) / Σ(wᵢ for i∈有数据)。
    全部缺失返回 None。
    """
    pairs = [
        (uptime, weights.uptime),
        (speed, weights.speed),
        (authenticity, weights.authenticity),
        (review, weights.review),
    ]
    num = 0.0
    den = 0.0
    for score, w in pairs:
        if score is not None and w > 0:
            num += score * w
            den += w
    if den == 0:
        return None
    return num / den


# ===== DB 侧：读探测数据 → 算分 → upsert site_scores =====

# 模型名子串 → 所属分榜（MVP 子串匹配；将来可换更细的归类表）
_FAMILY_KEYWORDS = {
    "claude": "claude",
    "gpt": "gpt",
    "gemini": "gemini",
}

# 算 uptime 回看的存活样本上限 / 算 speed·authenticity 的质量样本上限
_ALIVE_LOOKBACK = 2000
_QUALITY_LOOKBACK = 200


def _families_for(site: RelaySite) -> set[str]:
    """根据站点声明的模型，判断它该上哪些分榜。"""
    families: set[str] = set()
    for model in site.declared_models or []:
        low = str(model).lower()
        for family, kw in _FAMILY_KEYWORDS.items():
            if kw in low:
                families.add(family)
    return families


async def _weights_for(leaderboard: str) -> Weights:
    """取某榜权重；表里没有则用全 0（合成时该榜不产出有效分）。"""
    w = await LeaderboardWeight.filter(leaderboard=leaderboard).first()
    if w is None:
        return Weights(0.0, 0.0, 0.0, 0.0)
    return Weights(w.w_uptime, w.w_speed, w.w_authenticity, w.w_review)


# PLACEHOLDER_RECOMPUTE


async def recompute_site_scores(site: RelaySite) -> None:
    """重算某站在其归属各分榜的分数并 upsert site_scores。

    读 probe_results（alive 算 uptime；quality 算 speed/authenticity）+ reviews，
    调纯函数算分。各指标缺数据记 None（不补 0），由动态权重合成。
    """
    families = _families_for(site)
    if not families:
        return

    alive_rows = (
        await ProbeResult.filter(site_id=site.site_id, probe_type__in=["alive", "triggered"])
        .order_by("-probed_at")
        .limit(_ALIVE_LOOKBACK)
    )
    alive_samples = [AliveSample(probed_at=r.probed_at, is_alive=r.is_alive) for r in alive_rows]

    quality_rows = (
        await ProbeResult.filter(site_id=site.site_id, probe_type="quality")
        .order_by("-probed_at")
        .limit(_QUALITY_LOOKBACK)
    )
    quality_samples = [
        QualitySample(ttfb_ms=r.ttfb_ms, is_authentic=bool(r.is_authentic)) for r in quality_rows
    ]

    ratings = [
        float(r.rating) for r in await Review.filter(site_id=site.site_id, verified=True)
    ]

    up = uptime_score(alive_samples)
    sp = speed_score(quality_samples)
    au = authenticity_score(quality_samples)
    rv = review_score(ratings, global_mean=None)

    for family in families:
        weights = await _weights_for(family)
        comp = composite_score(uptime=up, speed=sp, authenticity=au, review=rv, weights=weights)
        existing = await SiteScore.filter(site_id=site.site_id, leaderboard=family).first()
        if existing is None:
            await SiteScore.create(
                site_id=site.site_id,
                leaderboard=family,
                uptime_score=up,
                speed_score=sp,
                authenticity_score=au,
                review_score=rv,
                composite_score=comp,
            )
        else:
            existing.uptime_score = up
            existing.speed_score = sp
            existing.authenticity_score = au
            existing.review_score = rv
            existing.composite_score = comp
            await existing.save(
                update_fields=[
                    "uptime_score",
                    "speed_score",
                    "authenticity_score",
                    "review_score",
                    "composite_score",
                    "updated_at",
                ]
            )


async def recompute_ranks(leaderboard: str) -> None:
    """按 composite 降序为某榜重算名次（仅主榜状态参与名次）。"""
    main_statuses = {"online", "abnormal", "revived"}
    scores = await SiteScore.filter(leaderboard=leaderboard)
    ranked = []
    for s in scores:
        site = await RelaySite.filter(site_id=s.site_id).first()
        if site and site.status in main_statuses and s.composite_score is not None:
            ranked.append(s)
    ranked.sort(key=lambda s: s.composite_score, reverse=True)
    for i, s in enumerate(ranked, start=1):
        s.rank = i
        await s.save(update_fields=["rank", "updated_at"])
