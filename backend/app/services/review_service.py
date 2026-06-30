"""评价业务逻辑。本阶段：B 端站长互评（owner_deal）。

红线（features.md 第 9 节）：评价权由真实交互解锁。
- owner_deal：集市对接 confirmed 才能评，且只能评帖子绑定的站点；
  对接两方（发帖人 + 对接人）各可评一次；evidence 来源即对接本身，故 verified=True。
- 写入后立即重算该站 review_score（沿用 C 端评分链路，与 user_topup 共用加权）。
"""

from app.models.marketplace_post import MarketplacePost
from app.models.post_response import PostResponse
from app.models.relay_site import RelaySite
from app.models.review import Review
from app.services.scoring import recompute_site_scores


class ReviewError(Exception):
    """评价业务错误基类。"""


class ResponseNotFound(ReviewError):
    """对接记录不存在。"""


class NotConfirmed(ReviewError):
    """对接未确认，互评权未解锁。"""


class NotDealParty(ReviewError):
    """非该对接的两方，无权评价。"""


class NoReviewTarget(ReviewError):
    """帖子未绑定站点，无可评对象。"""


class AlreadyReviewed(ReviewError):
    """已对该对接的站点评过价（防重复刷分）。"""


async def create_owner_deal_review(
    author_id: str,
    response_id: str,
    *,
    rating: int,
    content: str | None = None,
) -> Review:
    """B 端互评：confirmed 对接的两方评价帖子绑定的站点。

    校验链：对接存在 → confirmed → author 是两方之一 → 帖子绑定了站点 → 未重复评。
    写 Review(owner_deal, verified=True) 后刷新该站 review_score。
    """
    resp = await PostResponse.filter(response_id=response_id).first()
    if resp is None:
        raise ResponseNotFound(response_id)
    if resp.status != "confirmed":
        raise NotConfirmed(response_id)

    post = await MarketplacePost.filter(post_id=resp.post_id).first()
    if post is None:
        raise ResponseNotFound(str(resp.post_id))

    # author 必须是对接两方之一：发帖人 或 对接发起人
    parties = {str(post.author_id), str(resp.responder_id)}
    if str(author_id) not in parties:
        raise NotDealParty(response_id)

    if post.site_id is None:
        raise NoReviewTarget(response_id)

    # 防重复：同一作者对同一对接来源的同一站点只评一次。
    # 以 (author_id, site_id, owner_deal) 唯一约束近似——一个对接对应一个站点，
    # 同一对接两方各自一条，重复提交拦截。
    existing = await Review.filter(
        author_id=author_id,
        site_id=post.site_id,
        review_type="owner_deal",
    ).first()
    if existing is not None:
        raise AlreadyReviewed(response_id)

    review = await Review.create(
        site_id=post.site_id,
        author_id=author_id,
        review_type="owner_deal",
        rating=rating,
        content=content,
        verified=True,  # 对接 confirmed 本身即凭证
    )

    # 刷新该站 review_score（沿用 C 端评分链路）
    site = await RelaySite.filter(site_id=post.site_id).first()
    if site is not None:
        await recompute_site_scores(site)

    return review


async def list_site_reviews(site_id: str, *, verified_only: bool = True) -> list[Review]:
    """列某站评价（按时间倒序），供详情页展示，标注来源类型。

    公开详情页默认只展示 verified 评价；未验证评价不参与征信，也不公开背书。
    """
    query = Review.filter(site_id=site_id)
    if verified_only:
        query = query.filter(verified=True)
    return await query.order_by("-created_at")
