"""中转站上架业务逻辑：创建、查询站长自己的站点。

红线：api_key 经 encrypt_key 加密落库，明文用完即弃，
只保留 mask_key 生成的 key_hint 用于展示。
"""

import re

from tortoise import timezone

from app.core.security import encrypt_key, mask_key
from app.models.relay_site import RelaySite
from app.models.user import User


class SiteError(Exception):
    """站点相关业务错误基类。"""


class SlugAlreadyExists(SiteError):
    """slug 已被占用（仅统计未假删除的站点）。"""


class SiteNotFound(SiteError):
    """目标站点不存在（或已假删除）。"""


class SiteNotPending(SiteError):
    """站点不处于 pending 状态，无法审核。"""


def _slugify(name: str) -> str:
    """把站点名转成 URL 友好的 slug 基底：小写、非字母数字转连字符。"""
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s or "site"


async def _unique_slug(base: str) -> str:
    """在 base 基础上保证 slug 唯一：冲突则追加 -2、-3……

    只与未假删除的站点比较（默认管理器已过滤），最终由
    partial unique index 兜底。
    """
    candidate = base
    n = 1
    while await RelaySite.filter(slug=candidate).first() is not None:
        n += 1
        candidate = f"{base}-{n}"
    return candidate


async def create_site(
    owner_id: str,
    *,
    name: str,
    base_url: str,
    api_key: str,
    slug: str | None = None,
    site_url: str | None = None,
    declared_models: list[str] | None = None,
    min_topup=None,
    pay_methods: str | None = None,
    rpm_limit: int | None = None,
) -> RelaySite:
    """创建中转站：slug 处理 → key 加密 → 落库（status=pending 待审核/进观察区）。"""
    if slug:
        # 站长指定了 slug：冲突直接报错，不擅自改名
        if await RelaySite.filter(slug=slug).first() is not None:
            raise SlugAlreadyExists(slug)
        final_slug = slug
    else:
        final_slug = await _unique_slug(_slugify(name))

    site = await RelaySite.create(
        owner_id=owner_id,
        name=name,
        slug=final_slug,
        base_url=base_url,
        site_url=site_url,
        encrypted_key=encrypt_key(api_key),
        key_hint=mask_key(api_key),
        declared_models=declared_models,
        min_topup=min_topup,
        pay_methods=pay_methods,
        rpm_limit=rpm_limit,
        status="pending",
    )
    return site


async def list_owner_sites(owner_id: str) -> list[RelaySite]:
    """列出某站长名下的全部站点（按创建时间倒序）。"""
    return await RelaySite.filter(owner_id=owner_id).order_by("-created_at")


async def list_pending_sites() -> list[tuple[RelaySite, User | None]]:
    """列出全部待审核站点，并附其站长（虚拟外键在 service 层关联）。

    返回 (site, owner) 对；owner 可能为 None（站长已假删除等极端情况）。
    按创建时间正序，便于先到先审。
    """
    sites = await RelaySite.filter(status="pending").order_by("created_at")
    if not sites:
        return []
    owner_ids = {s.owner_id for s in sites}
    owners = await User.filter(user_id__in=list(owner_ids))
    owner_map = {str(o.user_id): o for o in owners}
    return [(s, owner_map.get(str(s.owner_id))) for s in sites]


async def review_site(site_id: str, *, approve: bool, note: str | None = None) -> RelaySite:
    """管理员审核站点：通过→observing，驳回→rejected（写 review_note）。

    仅 pending 站点可审核，否则抛 SiteNotPending；站点不存在抛 SiteNotFound。
    """
    site = await RelaySite.filter(site_id=site_id).first()
    if site is None:
        raise SiteNotFound(site_id)
    if site.status != "pending":
        raise SiteNotPending(site.status)

    if approve:
        site.status = "observing"
        site.review_note = None
        # 通过即进观察区，观察期计时从此刻起
        site.status_changed_at = timezone.now()
    else:
        site.status = "rejected"
        site.review_note = note
    await site.save(
        update_fields=["status", "review_note", "status_changed_at", "updated_at"]
    )
    return site
