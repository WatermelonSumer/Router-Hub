"""中转集市帖子模型（登录墙后，刻意不可 SEO，保护批发底价）。"""

from tortoise import fields

from app.models.base import BaseModel, SoftDeleteManager, gen_uuid7


class MarketplacePost(BaseModel):
    """站长广场（中转集市）帖子：批发倒卖 API 产能。

    结构化字段而非自由聊天，才能按维度筛选匹配（找上游=进货，找下游=出货）。
    """

    post_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    author_id = fields.UUIDField(db_index=True)  # 虚拟外键 → users.user_id

    post_type = fields.CharField(max_length=16)  # supply 出货 | demand 进货
    direction = fields.CharField(max_length=16)  # upstream | downstream
    model_family = fields.CharField(max_length=32, db_index=True)  # claude | gpt | gemini

    rate = fields.DecimalField(max_digits=8, decimal_places=4, null=True)  # 倍率
    rpm = fields.IntField(null=True)
    volume = fields.CharField(max_length=128, null=True)  # 量级：日均调用量/额度规模
    settlement = fields.CharField(max_length=16, null=True)  # daily | weekly | prepaid

    note = fields.TextField(null=True)  # 唯一自由文本
    status = fields.CharField(max_length=16, default="open", db_index=True)  # open | closed

    class Meta:
        table = "marketplace_posts"
        manager = SoftDeleteManager()
