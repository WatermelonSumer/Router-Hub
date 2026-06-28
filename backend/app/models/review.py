"""评价模型：C 端用户评价与 B 端站长互评共表，review_type 区分。"""

from tortoise import fields

from app.models.base import BaseModel, SoftDeleteManager, gen_uuid7


class Review(BaseModel):
    """评价（两类共表）。

    评价权必须由一次真实交互解锁，否则信誉系统当天被刷穿：
    - user_topup：用户用 key 自证在该站充过值（verified）。
    - owner_deal：站长在中转集市对接 confirmed 过（verified）。
    """

    review_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    site_id = fields.UUIDField(db_index=True)  # 虚拟外键 → relay_sites.site_id
    author_id = fields.UUIDField(db_index=True)  # 虚拟外键 → users.user_id

    review_type = fields.CharField(max_length=16)  # user_topup | owner_deal
    rating = fields.IntField()  # 1-5 星
    content = fields.TextField(null=True)

    verified = fields.BooleanField(default=False)  # 仅 verified 评价计入加权

    class Meta:
        table = "reviews"
        manager = SoftDeleteManager()
