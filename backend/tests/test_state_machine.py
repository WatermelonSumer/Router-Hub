"""状态机测试：穷举 blueprint 五之二各转移边（纯函数，不碰 DB）。"""

from app.core.config import settings
from app.worker.state_machine import ProbeStats, decide_transition


def _stats(**kw) -> ProbeStats:
    """构造 ProbeStats，未给字段填 0。"""
    base = dict(
        consecutive_fails=0,
        consecutive_successes=0,
        days_in_status=0.0,
        alive_probe_count=0,
        quality_probe_count=0,
    )
    base.update(kw)
    return ProbeStats(**base)


def test_online_to_abnormal():
    """online 连续失败达阈值 → abnormal。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_ABNORMAL)
    assert decide_transition("online", s) == "abnormal"


def test_online_stays_below_threshold():
    """online 失败未达阈值 → 不转移。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_ABNORMAL - 1)
    assert decide_transition("online", s) is None


def test_abnormal_recover_to_online():
    """abnormal 恢复成功达阈值 → online。"""
    s = _stats(consecutive_successes=settings.PROBE_RECOVER_FROM_ABNORMAL)
    assert decide_transition("abnormal", s) == "online"


def test_abnormal_to_suspected():
    """abnormal 持续失败累计达「疑似」阈值 → suspected_dead。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_SUSPECTED)
    assert decide_transition("abnormal", s) == "suspected_dead"


def test_suspected_recover_to_revived():
    """suspected_dead 恢复达阈值 → revived。"""
    s = _stats(consecutive_successes=settings.PROBE_RECOVER_FROM_SUSPECTED)
    assert decide_transition("suspected_dead", s) == "revived"


def test_suspected_to_dead():
    """suspected_dead 连续失败累计达阈值 → dead。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_DEAD)
    assert decide_transition("suspected_dead", s) == "dead"


def test_dead_recover_stricter():
    """dead 恢复要求更严：达 RECOVER_FROM_DEAD 才 revived。"""
    almost = _stats(consecutive_successes=settings.PROBE_RECOVER_FROM_DEAD - 1)
    assert decide_transition("dead", almost) is None
    ok = _stats(consecutive_successes=settings.PROBE_RECOVER_FROM_DEAD)
    assert decide_transition("dead", ok) == "revived"


def test_revived_flapping_back_to_suspected():
    """revived 再次连续失败达「疑似」阈值 → 直接打回 suspected_dead（无 abnormal 缓冲）。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_SUSPECTED)
    assert decide_transition("revived", s) == "suspected_dead"


def test_revived_stable_returns_online():
    """revived 稳定在线满观察期 → online。"""
    s = _stats(
        consecutive_successes=settings.PROBE_RECOVER_FROM_ABNORMAL,
        days_in_status=settings.REVIVED_STABLE_HOURS / 24.0 + 0.1,
    )
    assert decide_transition("revived", s) == "online"


def test_observing_graduation_and_conditions():
    """observing 毕业是「与」条件：成功+满天数+样本达标缺一不可。"""
    full = _stats(
        consecutive_successes=settings.PROBE_RECOVER_FROM_ABNORMAL,
        days_in_status=settings.OBSERVING_MIN_DAYS,
        alive_probe_count=settings.OBSERVING_MIN_ALIVE_PROBES,
        quality_probe_count=settings.OBSERVING_MIN_QUALITY_PROBES,
    )
    assert decide_transition("observing", full) == "online"

    # 样本不足 → 不毕业
    short = _stats(
        consecutive_successes=settings.PROBE_RECOVER_FROM_ABNORMAL,
        days_in_status=settings.OBSERVING_MIN_DAYS,
        alive_probe_count=settings.OBSERVING_MIN_ALIVE_PROBES - 1,
        quality_probe_count=settings.OBSERVING_MIN_QUALITY_PROBES,
    )
    assert decide_transition("observing", short) is None


def test_observing_sudden_death():
    """observing 连续失败达「疑似」阈值 → 直接 suspected_dead（跳过 abnormal）。"""
    s = _stats(consecutive_fails=settings.PROBE_FAIL_TO_SUSPECTED)
    assert decide_transition("observing", s) == "suspected_dead"


def test_pending_unaffected():
    """pending 不受探测影响（由 admin 审核负责）。"""
    s = _stats(consecutive_fails=999, consecutive_successes=999)
    assert decide_transition("pending", s) is None
