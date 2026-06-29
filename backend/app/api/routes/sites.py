"""中转站路由：站长上架、查看自己的站点。

红线：响应统一用 SiteOwnerView，绝不回传明文/密文 key。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_owner
from app.models.relay_site import RelaySite
from app.models.user import User
from app.schemas.site import SiteCreateRequest, SiteOwnerView
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
