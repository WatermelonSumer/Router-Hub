"""评分归一化测试：四指标算法边界 + 缺失数据动态权重（纯函数）。"""

from datetime import timedelta

from tortoise import timezone

from app.services.scoring import (
    AliveSample,
    QualitySample,
    Weights,
    authenticity_score,
    composite_score,
    review_score,
    speed_score,
    uptime_score,
)


def _alive(days_ago: float, ok: bool) -> AliveSample:
    return AliveSample(probed_at=timezone.now() - timedelta(days=days_ago), is_alive=ok)


def test_uptime_none_when_empty():
    """无样本 → None（不补 0）。"""
    assert uptime_score([]) is None


def test_uptime_all_alive_is_100():
    """全成功 → 100。"""
    samples = [_alive(0, True), _alive(1, True), _alive(2, True)]
    assert round(uptime_score(samples)) == 100


def test_uptime_time_weighted_recent_matters_more():
    """近期失败比远期失败更拉低分数（时间衰减加权）。"""
    recent_fail = [_alive(0, False), _alive(10, True)]
    old_fail = [_alive(0, True), _alive(10, False)]
    assert uptime_score(recent_fail) < uptime_score(old_fail)


def test_speed_none_without_authentic_samples():
    """无成功质量样本 → None。"""
    assert speed_score([QualitySample(ttfb_ms=None, is_authentic=False)]) is None


def test_speed_fast_full_score():
    """P90 ≤ 首拐点(1500ms) → 满分 100。"""
    samples = [QualitySample(ttfb_ms=800, is_authentic=True) for _ in range(10)]
    assert speed_score(samples) == 100.0


def test_speed_slower_lower_score():
    """更慢的 P90 给更低分。"""
    fast = [QualitySample(ttfb_ms=1000, is_authentic=True) for _ in range(10)]
    slow = [QualitySample(ttfb_ms=5000, is_authentic=True) for _ in range(10)]
    assert speed_score(slow) < speed_score(fast)


def test_authenticity_ratio():
    """真实性 = 成功比例 ×100。"""
    samples = [
        QualitySample(ttfb_ms=100, is_authentic=True),
        QualitySample(ttfb_ms=100, is_authentic=True),
        QualitySample(ttfb_ms=100, is_authentic=False),
        QualitySample(ttfb_ms=100, is_authentic=True),
    ]
    assert authenticity_score(samples) == 75.0


def test_authenticity_none_when_empty():
    assert authenticity_score([]) is None


def test_review_bayesian_dilutes_few_ratings():
    """评价少时被先验稀释：1 条 5 星不会顶满。"""
    score = review_score([5.0], global_mean=3.0)
    assert score is not None
    assert score < 100.0


def test_review_none_when_empty():
    assert review_score([], global_mean=3.0) is None


def test_composite_dynamic_weight_redistribution():
    """缺失指标不补 0：speed 缺失时只用有数据指标归一化。"""
    w = Weights(uptime=0.4, speed=0.4, authenticity=0.2, review=0.0)
    # speed=None：应只按 uptime+authenticity 的有效权重合成
    comp = composite_score(uptime=80, speed=None, authenticity=90, review=None, weights=w)
    expected = (80 * 0.4 + 90 * 0.2) / (0.4 + 0.2)
    assert round(comp, 4) == round(expected, 4)


def test_composite_none_when_all_missing():
    """全部指标缺失 → None。"""
    w = Weights(0.4, 0.4, 0.2, 0.0)
    result = composite_score(
        uptime=None, speed=None, authenticity=None, review=None, weights=w
    )
    assert result is None
