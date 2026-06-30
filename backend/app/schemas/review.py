"""评价相关 schema（两类共表，本阶段先落地 B 端站长互评 owner_deal）。

红线（features.md 第 9 节）：评价权必须由真实交互解锁，否则信誉系统当天被刷穿。
- owner_deal：集市对接 confirmed 解锁，对接两方互评帖子绑定的站点。
"""

from pydantic import BaseModel, Field


class ReviewCreateRequest(BaseModel):
    """发起一条评价：星级必填、文字可选。"""

    rating: int = Field(ge=1, le=5, description="1-5 星")
    content: str | None = Field(default=None, max_length=1000)


class UserTopupReviewCreateRequest(ReviewCreateRequest):
    """C 端评价请求：用户用自己在该站的 key 自证充值/用量。"""

    api_key: str = Field(min_length=8, max_length=4096)


class ReviewView(BaseModel):
    """评价视图。review_type 标注来源；verified 标注是否计入加权。"""

    review_id: str
    site_id: str
    author_id: str
    review_type: str  # user_topup | owner_deal
    rating: int
    content: str | None
    verified: bool
    created_at: str


class SiteReviewsResponse(BaseModel):
    """站点公开评价列表：只展示已验证评价。"""

    site_id: str
    reviews: list[ReviewView]
