"""中转集市路由：批发撮合市场（B 端，全程登录墙，刻意不 SEO）。

红线：所有接口要求 get_current_owner（仅站长，登录墙后）；
联系方式仅对接 confirmed 后通过名片交换。
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import get_current_owner, get_owner_or_admin
from app.models.marketplace_post import MarketplacePost
from app.models.post_response import PostResponse
from app.models.user import User
from app.schemas.marketplace import (
    ContactCard,
    OwnerReputation,
    PostCreateRequest,
    PostView,
    ResponseView,
)
from app.schemas.review import ReviewCreateRequest, ReviewView
from app.services.marketplace_service import (
    CannotRespondOwnPost,
    InvalidEnum,
    NotPostOwner,
    OwnerReputationData,
    PostClosed,
    PostNotFound,
    ResponseNotFound,
    close_post,
    confirm_response,
    create_post,
    list_my_responses,
    list_posts,
    list_responses_to_my_posts,
    reputation_for,
    respond_to_post,
)
from app.services.review_service import (
    AlreadyReviewed,
    NoReviewTarget,
    NotConfirmed,
    NotDealParty,
    create_owner_deal_review,
)
from app.services.review_service import (
    ResponseNotFound as ReviewResponseNotFound,
)

router = APIRouter(prefix="/market", tags=["market"])


def _to_reputation(data: OwnerReputationData) -> OwnerReputation:
    return OwnerReputation(
        best_composite=data.best_composite,
        max_alive_days=data.max_alive_days,
        site_count=data.site_count,
        graveyard_count=data.graveyard_count,
    )


def _to_post_view(
    post: MarketplacePost,
    rep: OwnerReputationData,
    viewer_id: str,
    site_info: dict[str, tuple[str, str]] | None = None,
) -> PostView:
    name = slug = None
    if post.site_id is not None and site_info is not None:
        pair = site_info.get(str(post.site_id))
        if pair is not None:
            name, slug = pair
    return PostView(
        post_id=str(post.post_id),
        author_id=str(post.author_id),
        site_id=str(post.site_id) if post.site_id is not None else None,
        site_name=name,
        site_slug=slug,
        post_type=post.post_type,
        direction=post.direction,
        model_family=post.model_family,
        rate=post.rate,
        rpm=post.rpm,
        volume=post.volume,
        settlement=post.settlement,
        note=post.note,
        status=post.status,
        created_at=post.created_at.isoformat(),
        is_mine=str(post.author_id) == str(viewer_id),
        author_reputation=_to_reputation(rep),
    )


async def _site_info_for(posts: list[MarketplacePost]) -> dict[str, tuple[str, str]]:
    """批量解析帖子绑定站点的 (name, slug)，供展示/链接。"""
    site_ids = {p.site_id for p in posts if p.site_id is not None}
    if not site_ids:
        return {}
    from app.models.relay_site import RelaySite

    sites = await RelaySite.filter(site_id__in=list(site_ids))
    return {str(s.site_id): (s.name, s.slug) for s in sites}


def _to_response_view(resp: PostResponse, contact_user: User | None) -> ResponseView:
    """对接记录转视图；contact 仅 confirmed 时由 service 给出 contact_user。"""
    contact = None
    if resp.status == "confirmed" and contact_user is not None:
        contact = ContactCard(
            user_id=str(contact_user.user_id),
            email=contact_user.email,
            wechat=contact_user.wechat,
            qq=contact_user.qq,
        )
    return ResponseView(
        response_id=str(resp.response_id),
        post_id=str(resp.post_id),
        responder_id=str(resp.responder_id),
        status=resp.status,
        created_at=resp.created_at.isoformat(),
        contact=contact,
    )


@router.post("/posts", response_model=PostView, status_code=status.HTTP_201_CREATED)
async def create(
    data: PostCreateRequest,
    owner: User = Depends(get_current_owner),
) -> PostView:
    """发布集市帖子。枚举非法返回 422。"""
    try:
        post = await create_post(
            str(owner.user_id),
            post_type=data.post_type,
            direction=data.direction,
            model_family=data.model_family,
            rate=data.rate,
            rpm=data.rpm,
            volume=data.volume,
            settlement=data.settlement,
            note=data.note,
        )
    except InvalidEnum as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"字段取值非法：{exc}",
        ) from exc
    # 新帖作者即当前站长，履历单独算
    rep = await reputation_for(str(owner.user_id))
    site_info = await _site_info_for([post])
    return _to_post_view(post, rep, str(owner.user_id), site_info)


@router.get("/posts", response_model=list[PostView])
async def posts(
    viewer: User = Depends(get_owner_or_admin),
    post_type: str | None = Query(default=None),
    direction: str | None = Query(default=None),
    model_family: str | None = Query(default=None),
    max_rate: Decimal | None = Query(default=None, ge=0),
    include_closed: bool = Query(default=False),
) -> list[PostView]:
    """按结构化字段筛选浏览帖子。站长（交易）与管理员（监管）均可读。"""
    pairs = await list_posts(
        post_type=post_type,
        direction=direction,
        model_family=model_family,
        max_rate=max_rate,
        include_closed=include_closed,
    )
    site_info = await _site_info_for([p for p, _ in pairs])
    return [_to_post_view(p, rep, str(viewer.user_id), site_info) for p, rep in pairs]


@router.post("/posts/{post_id}/close", response_model=PostView)
async def close(
    post_id: str,
    viewer: User = Depends(get_owner_or_admin),
) -> PostView:
    """关闭帖子。站长关自己的；管理员可关任意帖（内容下架/监管）。"""
    is_admin = viewer.role == "admin"
    try:
        post = await close_post(post_id, str(viewer.user_id), is_admin=is_admin)
    except PostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在") from exc
    except NotPostOwner as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只能关闭自己的帖子"
        ) from exc
    rep = await reputation_for(str(post.author_id))
    site_info = await _site_info_for([post])
    return _to_post_view(post, rep, str(viewer.user_id), site_info)


@router.post(
    "/posts/{post_id}/respond",
    response_model=ResponseView,
    status_code=status.HTTP_201_CREATED,
)
async def respond(
    post_id: str,
    owner: User = Depends(get_current_owner),
) -> ResponseView:
    """对帖子发起对接（pending）。不能对接自己的/已关闭的帖子。"""
    try:
        resp = await respond_to_post(post_id, str(owner.user_id))
    except PostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在") from exc
    except CannotRespondOwnPost as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="不能对接自己的帖子"
        ) from exc
    except PostClosed as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="该帖已关闭，无法对接"
        ) from exc
    return _to_response_view(resp, None)


@router.post("/responses/{response_id}/confirm", response_model=ResponseView)
async def confirm(
    response_id: str,
    owner: User = Depends(get_current_owner),
) -> ResponseView:
    """发帖人确认对接：confirmed，解锁换名片 + 互评权。"""
    try:
        resp = await confirm_response(response_id, str(owner.user_id))
    except ResponseNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对接记录不存在") from exc
    except PostNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="帖子不存在") from exc
    except NotPostOwner as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有发帖人能确认对接"
        ) from exc
    # 确认后，对接发起人是对手，返回其名片
    contact = await User.filter(user_id=resp.responder_id).first()
    return _to_response_view(resp, contact)


@router.get("/responses/mine", response_model=list[ResponseView])
async def my_responses(owner: User = Depends(get_current_owner)) -> list[ResponseView]:
    """我发起的对接（confirmed 含对手=发帖人的名片）。"""
    triples = await list_my_responses(str(owner.user_id))
    return [_to_response_view(r, contact) for r, _post, contact in triples]


@router.get("/responses/incoming", response_model=list[ResponseView])
async def incoming_responses(
    owner: User = Depends(get_current_owner),
) -> list[ResponseView]:
    """别人对我帖子的对接（confirmed 含对手=对接发起人的名片）。"""
    triples = await list_responses_to_my_posts(str(owner.user_id))
    return [_to_response_view(r, contact) for r, _post, contact in triples]


@router.post(
    "/responses/{response_id}/review",
    response_model=ReviewView,
    status_code=status.HTTP_201_CREATED,
)
async def review(
    response_id: str,
    data: ReviewCreateRequest,
    owner: User = Depends(get_current_owner),
) -> ReviewView:
    """B 端互评：confirmed 对接的两方评价帖子绑定的站点。

    解锁条件——必须是该对接两方之一且对接已 confirmed；每人每站一次。
    """
    try:
        rv = await create_owner_deal_review(
            str(owner.user_id),
            response_id,
            rating=data.rating,
            content=data.content,
        )
    except ReviewResponseNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="对接记录不存在") from exc
    except NotConfirmed as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="对接未确认，暂不能评价"
        ) from exc
    except NotDealParty as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="只有对接双方可以评价"
        ) from exc
    except NoReviewTarget as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="该帖未关联站点，无可评对象"
        ) from exc
    except AlreadyReviewed as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="你已评价过该站点"
        ) from exc
    return ReviewView(
        review_id=str(rv.review_id),
        site_id=str(rv.site_id),
        author_id=str(rv.author_id),
        review_type=rv.review_type,
        rating=rv.rating,
        content=rv.content,
        verified=rv.verified,
        created_at=rv.created_at.isoformat(),
    )
