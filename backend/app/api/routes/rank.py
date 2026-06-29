"""排行榜路由：游客可读的三大分榜（吃 SEO）。

无鉴权——榜单对所有人开放，是 C 端流量入口（blueprint 第四/八节）。
只暴露公开安全字段，绝不含 base_url / key / 站长信息。
"""

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.rank import RankEntry, RankResponse
from app.services.rank_service import (
    VALID_LEADERBOARDS,
    VALID_SORTS,
    RankEntryData,
    get_rankings,
)

router = APIRouter(prefix="/rank", tags=["rank"])


def _to_entry(data: RankEntryData) -> RankEntry:
    """RankEntryData 转响应 schema。"""
    return RankEntry(
        site_id=data.site_id,
        name=data.name,
        slug=data.slug,
        site_url=data.site_url,
        status=data.status,
        rank=data.rank,
        composite_score=data.composite_score,
        uptime_score=data.uptime_score,
        speed_score=data.speed_score,
        authenticity_score=data.authenticity_score,
        review_score=data.review_score,
        declared_models=data.declared_models,
    )


@router.get("", response_model=RankResponse)
async def rankings(
    leaderboard: str = Query(default="claude"),
    sort: str = Query(default="composite"),
) -> RankResponse:
    """读取某分榜：主榜 + 观察区试用榜分列返回。"""
    if leaderboard not in VALID_LEADERBOARDS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"未知分榜：{leaderboard}",
        )
    if sort not in VALID_SORTS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"未知排序键：{sort}",
        )

    main, observing = await get_rankings(leaderboard, sort)
    return RankResponse(
        leaderboard=leaderboard,
        sort=sort,
        main=[_to_entry(e) for e in main],
        observing=[_to_entry(e) for e in observing],
    )
