"""中转站路由：站长上架、查看自己的站点。

红线：响应统一用 SiteOwnerView，绝不回传明文/密文 key。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_owner, get_current_user
from app.models.relay_site import RelaySite
from app.models.user import User
from app.schemas.site import SiteCreateRequest, SiteOwnerView
from app.schemas.site_detail import (
    SiteGatedView,
    SitePublicView,
    SiteScoreBrief,
    UptimePoint,
)
from app.services.site_detail_service import (
    SiteDetailNotFound,
    get_gated_detail,
    get_public_detail,
)
from app.services.site_service import (
    SlugAlreadyExists,
    create_site,
    list_owner_sites,
)

router = APIRouter(prefix="/sites", tags=["sites"])


def _to_owner_view(site: RelaySite) -> SiteOwnerView:
    """ORM 站点对象转站长视角 schema（剔除 key）。"""
    return SiteOwnerView(
        site_id=str(site.site_id),
        name=site.name,
        slug=site.slug,
        base_url=site.base_url,
        site_url=site.site_url,
        key_hint=site.key_hint,
        status=site.status,
        review_note=site.review_note,
        declared_models=site.declared_models,
        min_topup=site.min_topup,
        pay_methods=site.pay_methods,
        rpm_limit=site.rpm_limit,
    )


@router.post("", response_model=SiteOwnerView, status_code=status.HTTP_201_CREATED)
async def create(
    data: SiteCreateRequest,
    owner: User = Depends(get_current_owner),
) -> SiteOwnerView:
    """站长上架中转站。新站初始 status=pending，等审核进入观察区。"""
    try:
        site = await create_site(
            owner_id=str(owner.user_id),
            name=data.name,
            base_url=data.base_url,
            api_key=data.api_key,
            slug=data.slug,
            site_url=data.site_url,
            declared_models=data.declared_models,
            min_topup=data.min_topup,
            pay_methods=data.pay_methods,
            rpm_limit=data.rpm_limit,
        )
    except SlugAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该 slug 已被占用，请换一个",
        ) from exc
    return _to_owner_view(site)


@router.get("/mine", response_model=list[SiteOwnerView])
async def mine(owner: User = Depends(get_current_owner)) -> list[SiteOwnerView]:
    """列出当前站长名下的全部站点。"""
    sites = await list_owner_sites(str(owner.user_id))
    return [_to_owner_view(s) for s in sites]


def _iso(dt) -> str | None:
    """datetime 转 ISO 字符串；None 透传。"""
    return dt.isoformat() if dt is not None else None


# 注意：以下 /{slug} 路由声明在 /mine 之后，确保字面量 /mine 优先匹配。


@router.get("/{slug}", response_model=SitePublicView)
async def public_detail(slug: str) -> SitePublicView:
    """站点详情（游客可见部分）。无鉴权——吃 SEO，是 C 端流量入口。

    绝不含 base_url / key；硬信息（价格/起充/限速/延迟）走 /{slug}/private。
    """
    try:
        data = await get_public_detail(slug)
    except SiteDetailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在",
        ) from exc

    site = data.site
    return SitePublicView(
        site_id=str(site.site_id),
        name=site.name,
        slug=site.slug,
        site_url=site.site_url,
        status=site.status,
        declared_models=site.declared_models,
        first_seen_at=_iso(site.first_seen_at),
        listed_at=site.created_at.isoformat(),
        last_probe_at=_iso(site.last_probe_at),
        status_changed_at=_iso(site.status_changed_at),
        verified=data.verified,
        uptime_30d=data.uptime_30d,
        uptime_history=[UptimePoint(date=d, uptime=u) for d, u in data.uptime_history],
        scores=[
            SiteScoreBrief(
                leaderboard=s.leaderboard,
                composite_score=s.composite_score,
                rank=s.rank,
            )
            for s in data.scores
        ],
    )


@router.get("/{slug}/private", response_model=SiteGatedView)
async def gated_detail(
    slug: str,
    _user: User = Depends(get_current_user),
) -> SiteGatedView:
    """站点硬信息（登录可见）：决策区 + 实测延迟。

    任意登录用户可见（注册转化钩子）；未登录由依赖抛 401，前端据此引导注册。
    红线：仍绝不含 key / base_url。
    """
    try:
        data = await get_gated_detail(slug)
    except SiteDetailNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="站点不存在",
        ) from exc

    site = data.site
    return SiteGatedView(
        site_id=str(site.site_id),
        slug=site.slug,
        min_topup=site.min_topup,
        pay_methods=site.pay_methods,
        rpm_limit=site.rpm_limit,
        ttfb_p50_ms=data.ttfb_p50_ms,
        ttfb_p90_ms=data.ttfb_p90_ms,
        latency_samples=data.latency_samples,
    )
