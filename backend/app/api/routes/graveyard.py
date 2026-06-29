"""坟场路由：游客可读的阵亡/疑似阵亡站点（吃 SEO，传播引爆点）。

无鉴权——坟场对所有人开放，是 C 端流量入口（features.md 第 5 节）。
只暴露公开安全字段，绝不含 base_url / key / 站长信息。
红线：客观探测事实措辞由前端承载；后端只按状态如实分流。
"""

from fastapi import APIRouter

from app.schemas.graveyard import GraveyardEntry, GraveyardResponse
from app.services.graveyard_service import GraveyardEntryData, list_graveyard

router = APIRouter(prefix="/graveyard", tags=["graveyard"])


def _to_entry(data: GraveyardEntryData) -> GraveyardEntry:
    """GraveyardEntryData 转响应 schema。"""
    return GraveyardEntry(
        site_id=data.site_id,
        name=data.name,
        slug=data.slug,
        site_url=data.site_url,
        status=data.status,
        declared_models=data.declared_models,
        first_seen_at=data.first_seen_at.isoformat() if data.first_seen_at else None,
        last_probe_at=data.last_probe_at.isoformat() if data.last_probe_at else None,
        status_changed_at=(
            data.status_changed_at.isoformat() if data.status_changed_at else None
        ),
    )


@router.get("", response_model=GraveyardResponse)
async def graveyard() -> GraveyardResponse:
    """读取坟场：疑似跑路 + 已确认阵亡分列两区，最近进入坟场的置顶。"""
    suspected, dead = await list_graveyard()
    return GraveyardResponse(
        suspected=[_to_entry(e) for e in suspected],
        dead=[_to_entry(e) for e in dead],
    )
