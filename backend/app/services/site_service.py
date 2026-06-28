"""中转站上架业务逻辑：创建、查询站长自己的站点。

红线：api_key 经 encrypt_key 加密落库，明文用完即弃，
只保留 mask_key 生成的 key_hint 用于展示。
"""

import re

from app.core.security import encrypt_key, mask_key
from app.models.relay_site import RelaySite


class SiteError(Exception):
    """站点相关业务错误基类。"""


class SlugAlreadyExists(SiteError):
    """slug 已被占用（仅统计未假删除的站点）。"""


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
