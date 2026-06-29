"""中转集市业务逻辑：发帖、筛选浏览、对接撮合（含换名片）。

红线（features.md 第 8/9 节）：
- 整个集市在登录墙后（路由层 get_current_owner 保证），不 SEO。
- 联系方式默认隐藏，仅对接 confirmed 后双方互换名片。
- 帖子旁挂发帖站长的探测履历（沿用 C 端征信）。
- 对接 confirmed 是 B 端互评的解锁凭证（本阶段只到 confirmed，互评下阶段做）。
"""

from datetime import datetime
from decimal import Decimal

from tortoise import timezone

from app.models.marketplace_post import MarketplacePost
from app.models.post_response import PostResponse
from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore
from app.models.user import User

# 合法枚举
VALID_POST_TYPES = ("supply", "demand")
VALID_DIRECTIONS = ("upstream", "downstream")
VALID_FAMILIES = ("claude", "gpt", "gemini")
VALID_SETTLEMENTS = ("daily", "weekly", "prepaid")

# 坟场态（算履历名片的污点数用）
_GRAVEYARD_STATUSES = ("suspected_dead", "dead")


class MarketError(Exception):
    """集市业务错误基类。"""


class PostNotFound(MarketError):
    """帖子不存在或已删除。"""


class ResponseNotFound(MarketError):
    """对接记录不存在。"""


class NotPostOwner(MarketError):
    """非发帖人，无权操作（关帖/确认对接）。"""


class InvalidEnum(MarketError):
    """枚举字段取值非法。"""


class CannotRespondOwnPost(MarketError):
    """不能对接自己的帖子。"""


class PostClosed(MarketError):
    """帖子已关闭，不能再对接。"""


class OwnerReputationData:
    """发帖站长履历名片的数据载体。"""

    def __init__(
        self,
        *,
        best_composite: float | None,
        max_alive_days: int | None,
        site_count: int,
        graveyard_count: int,
    ):
        self.best_composite = best_composite
        self.max_alive_days = max_alive_days
        self.site_count = site_count
        self.graveyard_count = graveyard_count


async def reputation_for(author_id: str) -> OwnerReputationData:
    """汇总某站长名下站点的探测履历（沿用 C 端征信）。"""
    sites = await RelaySite.filter(owner_id=author_id)
    site_count = len(sites)
    if site_count == 0:
        return OwnerReputationData(
            best_composite=None, max_alive_days=None, site_count=0, graveyard_count=0
        )

    site_ids = [s.site_id for s in sites]
    graveyard_count = sum(1 for s in sites if s.status in _GRAVEYARD_STATUSES)

    # 最长存活天数：以 first_seen_at 起算
    now = timezone.now()
    alive_days_list = [
        int((now - s.first_seen_at).total_seconds() // 86400)
        for s in sites
        if s.first_seen_at is not None
    ]
    max_alive_days = max(alive_days_list) if alive_days_list else None

    # 名下站点跨榜最高综合分
    scores = await SiteScore.filter(site_id__in=site_ids)
    composites = [s.composite_score for s in scores if s.composite_score is not None]
    best_composite = max(composites) if composites else None

    return OwnerReputationData(
        best_composite=best_composite,
        max_alive_days=max_alive_days,
        site_count=site_count,
        graveyard_count=graveyard_count,
    )


def _validate_post_enums(
    post_type: str, direction: str, model_family: str, settlement: str | None
) -> None:
    """校验帖子枚举字段；非法抛 InvalidEnum。"""
    if post_type not in VALID_POST_TYPES:
        raise InvalidEnum(f"post_type={post_type}")
    if direction not in VALID_DIRECTIONS:
        raise InvalidEnum(f"direction={direction}")
    if model_family not in VALID_FAMILIES:
        raise InvalidEnum(f"model_family={model_family}")
    if settlement is not None and settlement not in VALID_SETTLEMENTS:
        raise InvalidEnum(f"settlement={settlement}")


async def create_post(
    author_id: str,
    *,
    post_type: str,
    direction: str,
    model_family: str,
    rate: Decimal | None = None,
    rpm: int | None = None,
    volume: str | None = None,
    settlement: str | None = None,
    note: str | None = None,
) -> MarketplacePost:
    """发布集市帖子（status=open）。枚举非法抛 InvalidEnum。

    自动绑定发帖人名下站点（当前一人一站，取其一）作为互评对象 site_id；
    无站点（纯买家）则 site_id 留空，该帖不可被互评。
    """
    _validate_post_enums(post_type, direction, model_family, settlement)
    # 取发帖人名下站点（按创建时间，取第一个）。一人一站时即唯一站点。
    site = await RelaySite.filter(owner_id=author_id).order_by("created_at").first()
    return await MarketplacePost.create(
        author_id=author_id,
        site_id=site.site_id if site is not None else None,
        post_type=post_type,
        direction=direction,
        model_family=model_family,
        rate=rate,
        rpm=rpm,
        volume=volume,
        settlement=settlement,
        note=note,
        status="open",
    )


async def list_posts(
    *,
    post_type: str | None = None,
    direction: str | None = None,
    model_family: str | None = None,
    max_rate: Decimal | None = None,
    include_closed: bool = False,
) -> list[tuple[MarketplacePost, OwnerReputationData]]:
    """按结构化字段筛选帖子，附发帖人履历名片。按发布时间倒序。

    默认只列 open 帖；max_rate 过滤「倍率 ≤ X」（rate 为 None 的帖不被该过滤剔除）。
    """
    query = MarketplacePost.all()
    if not include_closed:
        query = query.filter(status="open")
    if post_type:
        query = query.filter(post_type=post_type)
    if direction:
        query = query.filter(direction=direction)
    if model_family:
        query = query.filter(model_family=model_family)
    if max_rate is not None:
        query = query.filter(rate__lte=max_rate)

    posts = await query.order_by("-created_at")
    if not posts:
        return []

    # 批量算各发帖人履历（去重 author_id，避免 N+1）
    author_ids = {p.author_id for p in posts}
    rep_map = {aid: await reputation_for(str(aid)) for aid in author_ids}
    return [(p, rep_map[p.author_id]) for p in posts]


async def close_post(
    post_id: str, requester_id: str, *, is_admin: bool = False
) -> MarketplacePost:
    """关闭帖子。站长仅能关自己的；管理员可关任意帖（内容下架/监管）。"""
    post = await MarketplacePost.filter(post_id=post_id).first()
    if post is None:
        raise PostNotFound(post_id)
    if not is_admin and str(post.author_id) != str(requester_id):
        raise NotPostOwner(post_id)
    post.status = "closed"
    await post.save(update_fields=["status", "updated_at"])
    return post


async def respond_to_post(post_id: str, responder_id: str) -> PostResponse:
    """对帖子发起对接（status=pending）。

    不能对接自己的帖子；已关闭帖不能对接；重复对接返回已有记录（幂等）。
    """
    post = await MarketplacePost.filter(post_id=post_id).first()
    if post is None:
        raise PostNotFound(post_id)
    if str(post.author_id) == str(responder_id):
        raise CannotRespondOwnPost(post_id)
    if post.status != "open":
        raise PostClosed(post_id)

    existing = await PostResponse.filter(
        post_id=post_id, responder_id=responder_id
    ).first()
    if existing is not None:
        return existing

    return await PostResponse.create(
        post_id=post_id, responder_id=responder_id, status="pending"
    )


async def confirm_response(response_id: str, requester_id: str) -> PostResponse:
    """发帖人确认对接：pending/connected → confirmed，解锁双方换名片 + 互评权。

    仅该帖发帖人可确认。
    """
    resp = await PostResponse.filter(response_id=response_id).first()
    if resp is None:
        raise ResponseNotFound(response_id)
    post = await MarketplacePost.filter(post_id=resp.post_id).first()
    if post is None:
        raise PostNotFound(str(resp.post_id))
    if str(post.author_id) != str(requester_id):
        raise NotPostOwner(response_id)

    resp.status = "confirmed"
    await resp.save(update_fields=["status", "updated_at"])
    return resp


async def _contact_of(user_id: str) -> User | None:
    """取某用户的联系方式（仅 confirmed 后由上层调用）。"""
    return await User.filter(user_id=user_id).first()


async def list_my_responses(
    requester_id: str,
) -> list[tuple[PostResponse, MarketplacePost | None, User | None]]:
    """列出当前站长发起的对接 + 对应帖子 + 对手名片（confirmed 才含名片）。

    对手 = 帖子发帖人。confirmed 时返回发帖人 User 供换名片，否则 None。
    """
    responses = await PostResponse.filter(responder_id=requester_id).order_by("-created_at")
    return await _attach_post_and_contact(responses, counterpart="author")


async def list_responses_to_my_posts(
    requester_id: str,
) -> list[tuple[PostResponse, MarketplacePost | None, User | None]]:
    """列出别人对「我的帖子」发起的对接 + 帖子 + 对手名片（confirmed 才含）。

    对手 = 对接发起人（responder）。
    """
    my_posts = await MarketplacePost.filter(author_id=requester_id)
    if not my_posts:
        return []
    post_ids = [p.post_id for p in my_posts]
    responses = await PostResponse.filter(post_id__in=post_ids).order_by("-created_at")
    return await _attach_post_and_contact(responses, counterpart="responder")


async def _attach_post_and_contact(
    responses: list[PostResponse], *, counterpart: str
) -> list[tuple[PostResponse, MarketplacePost | None, User | None]]:
    """给对接记录附帖子与对手名片（仅 confirmed 给名片）。

    counterpart="author"：对手是发帖人；"responder"：对手是对接发起人。
    """
    if not responses:
        return []
    post_ids = {r.post_id for r in responses}
    posts = await MarketplacePost.filter(post_id__in=list(post_ids))
    post_map = {str(p.post_id): p for p in posts}

    result = []
    for r in responses:
        post = post_map.get(str(r.post_id))
        contact: User | None = None
        if r.status == "confirmed":
            if counterpart == "author" and post is not None:
                contact = await _contact_of(str(post.author_id))
            elif counterpart == "responder":
                contact = await _contact_of(str(r.responder_id))
        result.append((r, post, contact))
    return result


def _iso(dt: datetime | None) -> str | None:
    """datetime 转 ISO；None 透传。"""
    return dt.isoformat() if dt is not None else None
