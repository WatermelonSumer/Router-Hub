"""管理员审核路由：列待审站点、通过/驳回。

红线：仅 admin 角色可访问；列表会附站长联系方式（审核触达所需，
默认隐藏的联系方式在此对管理员开放），但响应仍绝不含任何形态的 key。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_admin
from app.models.relay_site import RelaySite
from app.models.user import User
from app.schemas.site import SiteAdminView, SiteOwnerView, SiteRejectRequest
from app.services.site_service import (
    SiteNotFound,
    SiteNotPending,
    list_pending_sites,
    review_site,
)

router = APIRouter(prefix="/admin/sites", tags=["admin"])


def _to_admin_view(site: RelaySite, owner: User | None) -> SiteAdminView:
    """ORM 站点 + 站长转管理员视角 schema（剔除 key）。"""
    return SiteAdminView(
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
        owner_id=str(site.owner_id),
        owner_email=owner.email if owner else None,
        owner_wechat=owner.wechat if owner else None,
        owner_qq=owner.qq if owner else None,
        created_at=site.created_at.isoformat(),
    )


def _to_owner_view(site: RelaySite) -> SiteOwnerView:
    """审核后回传站点的站长视角（不含 key、不含站长联系方式）。"""
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


@router.get("/pending", response_model=list[SiteAdminView])
async def pending(_: User = Depends(get_current_admin)) -> list[SiteAdminView]:
    """列出全部待审核（pending）站点，先到先审。"""
    pairs = await list_pending_sites()
    return [_to_admin_view(site, owner) for site, owner in pairs]


@router.post("/{site_id}/approve", response_model=SiteOwnerView)
async def approve(
    site_id: str,
    _: User = Depends(get_current_admin),
) -> SiteOwnerView:
    """审核通过：pending → observing，进入冷启动观察区。"""
    try:
        site = await review_site(site_id, approve=True)
    except SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在") from exc
    except SiteNotPending as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该站点不处于待审核状态",
        ) from exc
    return _to_owner_view(site)


@router.post("/{site_id}/reject", response_model=SiteOwnerView)
async def reject(
    site_id: str,
    data: SiteRejectRequest,
    _: User = Depends(get_current_admin),
) -> SiteOwnerView:
    """审核驳回：pending → rejected，理由写入 review_note 回传站长。"""
    try:
        site = await review_site(site_id, approve=False, note=data.note)
    except SiteNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="站点不存在") from exc
    except SiteNotPending as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该站点不处于待审核状态",
        ) from exc
    return _to_owner_view(site)
