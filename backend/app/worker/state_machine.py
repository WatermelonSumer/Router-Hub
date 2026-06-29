"""探测判定状态机（纯函数）：照搬 blueprint 五之二转移表。

核心原则：状态转移由「连续探测结果次数」驱动，不由时间驱动（时间仅辅助）。
本模块不碰 DB、不碰网络，只做判定，便于穷举单测各转移边。
pending → observing 由 admin 审核负责（见 services/site_service.review_site），不在此。
"""

from dataclasses import dataclass

from app.core.config import settings


@dataclass
class ProbeStats:
    """喂给状态机的探测统计（由 probe_stats 从 probe_results 算好）。"""

    consecutive_fails: int  # 最近连续失败次数（维护窗内失败已剔除）
    consecutive_successes: int  # 最近连续成功次数
    days_in_status: float  # 在当前状态停留的天数（observing 毕业、revived 观察期用）
    alive_probe_count: int  # observing 期间累计存活探测样本数
    quality_probe_count: int  # observing 期间累计质量探测样本数


def decide_transition(status: str, stats: ProbeStats) -> str | None:
    """根据当前状态与探测统计，返回应转入的新状态；无需转移返回 None。

    阈值全部来自 settings（.env 可调）。
    """
    s = settings
    f = stats.consecutive_fails
    ok = stats.consecutive_successes

    if status == "observing":
        # 毕业是「与」条件：连续成功 + 满天数 + 样本达标
        graduated = (
            ok >= s.PROBE_RECOVER_FROM_ABNORMAL
            and stats.days_in_status >= s.OBSERVING_MIN_DAYS
            and stats.alive_probe_count >= s.OBSERVING_MIN_ALIVE_PROBES
            and stats.quality_probe_count >= s.OBSERVING_MIN_QUALITY_PROBES
        )
        if graduated:
            return "online"
        # 新站直接暴毙，跳过 abnormal
        if f >= s.PROBE_FAIL_TO_SUSPECTED:
            return "suspected_dead"
        return None

    if status == "online":
        if f >= s.PROBE_FAIL_TO_ABNORMAL:
            return "abnormal"
        return None

    if status == "abnormal":
        # 抖动恢复优先判定
        if ok >= s.PROBE_RECOVER_FROM_ABNORMAL:
            return "online"
        if f >= s.PROBE_FAIL_TO_SUSPECTED:
            return "suspected_dead"
        return None

    if status == "suspected_dead":
        if ok >= s.PROBE_RECOVER_FROM_SUSPECTED:
            return "revived"
        if f >= s.PROBE_FAIL_TO_DEAD:
            return "dead"
        return None

    if status == "dead":
        # 死而复生要求更严
        if ok >= s.PROBE_RECOVER_FROM_DEAD:
            return "revived"
        return None

    if status == "revived":
        # 反复横跳：再次连续失败达「疑似」阈值，不给 abnormal 缓冲直接打回
        if f >= s.PROBE_FAIL_TO_SUSPECTED:
            return "suspected_dead"
        # 稳定在线满观察期 → 回归 online（污点由历史记录永久保留，不在状态里）
        if ok >= s.PROBE_RECOVER_FROM_ABNORMAL and stats.days_in_status >= (
            s.REVIVED_STABLE_HOURS / 24.0
        ):
            return "online"
        return None

    # pending 等其余状态：探测不改其状态
    return None
