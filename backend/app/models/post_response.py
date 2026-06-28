"""集市对接记录模型（解锁 B 端互评的凭证）。"""

from tortoise import fields

from app.models.base import BaseModel, gen_uuid7


class PostResponse(BaseModel):
    """广场对接记录。

    双方 confirmed 后才解锁彼此的 owner_deal 评价权 + 交换微信/QQ 名片。
    状态机：pending → connected → confirmed。
    """

    response_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    post_id = fields.UUIDField(db_index=True)  # 虚拟外键 → marketplace_posts.post_id
    responder_id = fields.UUIDField(db_index=True)  # 虚拟外键 → users.user_id

    status = fields.CharField(max_length=16, default="pending")  # pending | connected | confirmed

    class Meta(BaseModel.Meta):
        abstract = False
        table = "post_responses"
