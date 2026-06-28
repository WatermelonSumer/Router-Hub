"""探测函数桩。

本轮仅结构化日志，不真探测、不连上游、不用站长 key。
真实探测逻辑（httpx 并发、TTFB 测量、状态机判定、预算扣减）留后续实现，
对应 blueprint 第五节探测 worker 流程与第五之二状态机。
"""

import logging

logger = logging.getLogger("router_hub.worker")


async def run_alive_probe() -> None:
    """存活探测轮（桩）：将拉取 online/observing 站并发打 /v1/models。"""
    logger.info("[alive] 存活探测轮触发（桩，未实现真实探测）")


async def run_quality_probe() -> None:
    """质量探测轮（桩）：将用站长 key 打 /v1/chat 测 TTFB/真实性，并扣每日预算。"""
    logger.info("[quality] 质量探测轮触发（桩，未实现真实探测）")


async def run_triggered_probe(site_id: str) -> None:
    """触发探测（桩）：存活探测发现连续失败时插队，快速判定真宕机 vs 误报。"""
    logger.info("[triggered] 触发探测 site_id=%s（桩，未实现真实探测）", site_id)
