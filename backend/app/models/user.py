"""用户模型：普通用户与站长共表，role 区分。"""

from tortoise import fields

from app.models.base import BaseModel, SoftDeleteManager, gen_uuid7


class User(BaseModel):
    """用户与站长共用一张表，role=user|owner。

    站长（owner）必填 wechat/qq，但联系方式默认隐藏，
    仅在中转集市对接 confirmed 后作为名片交换。
    """

    user_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)

    email = fields.CharField(max_length=255)  # 唯一性走 partial unique index（见迁移）
    password_hash = fields.CharField(max_length=255)
    role = fields.CharField(max_length=16, default="user")  # user | owner

    # 站长联系方式：必填但默认隐藏，不公开展示
    wechat = fields.CharField(max_length=128, null=True)
    qq = fields.CharField(max_length=32, null=True)

    class Meta:
        table = "users"
        manager = SoftDeleteManager()
