"""中转集市相关 schema（B 端，登录墙后，刻意不 SEO，保护批发底价）。

帖子结构化（非自由聊天）才能按维度筛选匹配。
红线（features.md 第 8/9 节）：
- 联系方式默认隐藏，仅对接 confirmed 后作为名片交换。
- 帖子旁挂发帖站长的探测履历（带履历的名片，非裸联系方式）。
"""

from decimal import Decimal

from pydantic import BaseModel, Field

# 枚举取值由路由/service 层校验
PostType = str  # supply 出货 | demand 进货
Direction = str  # upstream 上游 | downstream 下游
ModelFamily = str  # claude | gpt | gemini
Settlement = str  # daily | weekly | prepaid


class OwnerReputation(BaseModel):
    """发帖站长的探测履历名片（沿用 C 端征信，挂在帖子旁）。

    不含联系方式（对接 confirmed 才给）；不含任何 key/base_url。
    """

    best_composite: float | None  # 名下站点最高综合分（跨榜取最大）
    max_alive_days: int | None  # 名下站点最长存活天数
    site_count: int  # 名下在册站点数
    graveyard_count: int  # 名下处于坟场态（疑似/阵亡）的站点数


class PostCreateRequest(BaseModel):
    """发布集市帖子。供给帖/需求帖共用一套结构化字段。"""

    post_type: str = Field(description="supply 出货 | demand 进货")
    direction: str = Field(description="upstream 上游 | downstream 下游")
    model_family: str = Field(description="claude | gpt | gemini")
    rate: Decimal | None = Field(default=None, ge=0, description="倍率")
    rpm: int | None = Field(default=None, ge=0)
    volume: str | None = Field(default=None, max_length=128, description="量级")
    settlement: str | None = Field(default=None, description="daily | weekly | prepaid")
    note: str | None = Field(default=None, max_length=1000, description="唯一自由文本")


class PostView(BaseModel):
    """集市帖子视图：结构化字段 + 发帖人履历名片。

    绝不含发帖人联系方式（对接 confirmed 后通过 ResponseView 单独交换）。
    """

    post_id: str
    author_id: str
    post_type: str
    direction: str
    model_family: str
    rate: Decimal | None
    rpm: int | None
    volume: str | None
    settlement: str | None
    note: str | None
    status: str  # open | closed
    created_at: str
    is_mine: bool  # 当前登录站长是否为发帖人（前端区分操作）
    author_reputation: OwnerReputation


class ContactCard(BaseModel):
    """对接 confirmed 后交换的名片：联系方式（红线——仅此处、仅 confirmed 可见）。"""

    user_id: str
    email: str
    wechat: str | None
    qq: str | None


class ResponseView(BaseModel):
    """对接记录视图。

    contact 仅在 status=confirmed 时填充（双方互见名片），否则为 None。
    """

    response_id: str
    post_id: str
    responder_id: str
    status: str  # pending | connected | confirmed
    created_at: str
    contact: ContactCard | None  # confirmed 才给
