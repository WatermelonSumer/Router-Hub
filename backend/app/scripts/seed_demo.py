"""填充演示数据，让排行榜在探测 worker 就绪前就有内容可看。

用法：
    poetry run python -m app.scripts.seed_demo          # 幂等填充（已存在则跳过）
    poetry run python -m app.scripts.seed_demo --wipe   # 先清演示数据再填充

设计：
- 幂等：以固定 slug 为锚，重复运行不重复造站。
- 仅演示用：站点 key 为占位假值（加密落库走真实加密路径），base_url 不可探测。
  worker 上线后这些演示站会探测失败，可用 --wipe 清掉换真实站点。
- 造三榜权重（leaderboard_weights）+ 各状态站点 + 预计算分（site_scores），
  分数手工编排出合理排名，覆盖 online/abnormal/observing 各状态。
"""

import argparse
import asyncio
import sys

from tortoise import Tortoise, timezone

from app.core.db import TORTOISE_ORM
from app.core.security import encrypt_key, mask_key
from app.models.leaderboard_weight import LeaderboardWeight
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore

# 演示数据统一锚定一个假 owner_id（不建真实用户，避免污染登录）
_DEMO_OWNER_ID = "00000000-0000-0000-0000-0000000000de"
_DEMO_KEY = "sk-demo-placeholder-0000"  # 占位假 key，仅为走通加密路径

# 三榜权重（blueprint 3.3：Claude 抬真实性 / GPT 抬在线率价格 / Gemini 抬在线率）
_WEIGHTS = {
    "claude": dict(w_uptime=0.30, w_speed=0.15, w_authenticity=0.45, w_review=0.10),
    "gpt": dict(w_uptime=0.40, w_speed=0.25, w_authenticity=0.25, w_review=0.10),
    "gemini": dict(w_uptime=0.50, w_speed=0.20, w_authenticity=0.20, w_review=0.10),
}

# PLACEHOLDER_DATA

# 演示站点：slug 为幂等锚。每站给定状态 + 各榜分数（缺则该榜不出现）。
# scores: {leaderboard: (uptime, speed, authenticity, review, composite)}
_DEMO_SITES = [
    {
        "name": "StellarRelay",
        "slug": "stellar-relay",
        "status": "online",
        "models": ["claude-3-5-sonnet", "gpt-4o", "gemini-1.5-pro"],
        "scores": {
            "claude": (98, 86, 99, 92, 96.1),
            "gpt": (98, 86, 95, 92, 94.3),
            "gemini": (98, 86, 95, 92, 95.0),
        },
    },
    {
        "name": "NovaGateway",
        "slug": "nova-gateway",
        "status": "online",
        "models": ["claude-3-5-sonnet", "gpt-4o"],
        "scores": {
            "claude": (95, 92, 90, 80, 91.5),
            "gpt": (95, 92, 88, 80, 91.2),
        },
    },
    {
        "name": "QuasarHub",
        "slug": "quasar-hub",
        "status": "abnormal",
        "models": ["gpt-4o", "gemini-1.5-pro"],
        "scores": {
            "gpt": (72, 78, 80, 70, 75.4),
            "gemini": (72, 78, 80, 70, 74.0),
        },
    },
    {
        "name": "PulsarAPI",
        "slug": "pulsar-api",
        "status": "online",
        "models": ["claude-3-5-sonnet"],
        "scores": {
            "claude": (88, 70, 94, 60, 87.4),
        },
    },
    {
        "name": "CometProxy",
        "slug": "comet-proxy",
        "status": "observing",
        "models": ["claude-3-5-sonnet", "gpt-4o"],
        # 观察区新站：暂无速度数据（null），考验缺失数据展示
        "scores": {
            "claude": (90, None, 85, None, 88.0),
            "gpt": (90, None, 82, None, 86.5),
        },
    },
]


async def _wipe() -> None:
    """物理删除全部演示数据（按 demo owner_id / 锚 slug 锁定范围）。"""
    sites = await RelaySite.all_objects().filter(owner_id=_DEMO_OWNER_ID)
    site_ids = [s.site_id for s in sites]
    if site_ids:
        await SiteScore.all_objects().filter(site_id__in=site_ids).delete()
    await RelaySite.all_objects().filter(owner_id=_DEMO_OWNER_ID).delete()
    print(f"已清除 {len(site_ids)} 个演示站点及其分数。")


async def _seed_weights() -> None:
    """幂等填充三榜权重。"""
    for board, w in _WEIGHTS.items():
        existing = await LeaderboardWeight.filter(leaderboard=board).first()
        if existing is None:
            await LeaderboardWeight.create(leaderboard=board, **w)
            print(f"  权重 {board} 已创建")
        else:
            print(f"  权重 {board} 已存在，跳过")


async def _seed_sites() -> None:
    """幂等填充演示站点与分数（以 slug 为锚）。"""
    for spec in _DEMO_SITES:
        site = await RelaySite.filter(slug=spec["slug"]).first()
        if site is None:
            site = await RelaySite.create(
                owner_id=_DEMO_OWNER_ID,
                name=spec["name"],
                slug=spec["slug"],
                base_url=f"https://{spec['slug']}.demo.invalid/v1",
                site_url=f"https://{spec['slug']}.demo.invalid",
                encrypted_key=encrypt_key(_DEMO_KEY),
                key_hint=mask_key(_DEMO_KEY),
                declared_models=spec["models"],
                status=spec["status"],
                status_changed_at=timezone.now(),
            )
            print(f"  站点 {spec['name']} 已创建（{spec['status']}）")
        else:
            print(f"  站点 {spec['name']} 已存在，跳过建站")

        for board, (uptime, speed, auth, review, composite) in spec["scores"].items():
            score = await SiteScore.filter(
                site_id=site.site_id, leaderboard=board
            ).first()
            if score is None:
                await SiteScore.create(
                    site_id=site.site_id,
                    leaderboard=board,
                    uptime_score=uptime,
                    speed_score=speed,
                    authenticity_score=auth,
                    review_score=review,
                    composite_score=composite,
                )

    # 各榜按 composite 重算 rank（仅主榜状态参与名次）
    await _recompute_ranks()


async def _recompute_ranks() -> None:
    """按 composite 降序为每个榜重算 rank（演示用，worker 上线后由其负责）。"""
    main_statuses = {"online", "abnormal", "revived"}
    for board in _WEIGHTS:
        scores = await SiteScore.filter(leaderboard=board)
        ranked = []
        for s in scores:
            site = await RelaySite.filter(site_id=s.site_id).first()
            if site and site.status in main_statuses and s.composite_score is not None:
                ranked.append(s)
        ranked.sort(key=lambda s: s.composite_score, reverse=True)
        for i, s in enumerate(ranked, start=1):
            s.rank = i
            await s.save(update_fields=["rank", "updated_at"])


async def _run(wipe: bool) -> int:
    """连接数据库并填充演示数据。"""
    await Tortoise.init(config=TORTOISE_ORM)
    try:
        if wipe:
            await _wipe()
        print("填充三榜权重：")
        await _seed_weights()
        print("填充演示站点与分数：")
        await _seed_sites()
        print("完成。访问 /rank?leaderboard=claude 查看。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> None:
    """解析参数并执行。"""
    parser = argparse.ArgumentParser(description="填充排行榜演示数据")
    parser.add_argument(
        "--wipe",
        action="store_true",
        help="先清除已有演示数据再填充",
    )
    args = parser.parse_args()
    sys.exit(asyncio.run(_run(args.wipe)))


if __name__ == "__main__":
    main()

