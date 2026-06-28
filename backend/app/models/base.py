"""模型基类与通用约定。

强制约定（所有表无例外，见 docs/dev/blueprint.md 第三节 / 项目记忆 data-layer-conventions）：
1. 双键制：内部 bigint 自增 id（不对外）+ <实体>_id（uuid7 有序业务键，对外）。
2. 虚拟外键：DB 层零外键约束，关联只存对方业务键值，完整性在 service 层保证。
3. 假删除：全表 is_deleted + deleted_at，查询默认过滤 is_deleted=False。
4. 时间戳：全表 created_at + updated_at。
5. uuid7 用 uuid-utils（Rust 实现）。
"""

import uuid

import uuid_utils
from tortoise import fields
from tortoise.manager import Manager
from tortoise.models import Model
from tortoise.queryset import QuerySet


def gen_uuid7() -> uuid.UUID:
    """生成有序 uuid7，转成标准库 uuid.UUID 以兼容 Tortoise 的 UUIDField。"""
    return uuid.UUID(str(uuid_utils.uuid7()))


class SoftDeleteManager(Manager):
    """默认管理器：自动过滤掉已假删除的行。

    需要访问全量（含已删除）时用 BaseModel.all_objects()。
    """

    def get_queryset(self) -> QuerySet:
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(Model):
    """所有业务表的抽象基类，封装双键制、软删除、时间戳。

    软删除依赖 SoftDeleteManager。Tortoise 的 Manager 按模型绑定 _model，
    多个模型【不能共享同一个实例】（否则 _model 互相覆盖，filter 会串到别的表）。
    因此每个具体模型必须在自己的 Meta 里写独立的 `manager = SoftDeleteManager()`，
    并 `abstract = False`。不要用 `class Meta(BaseModel.Meta)` 继承，那会共享实例。
    """

    # 内部主键：仅 ORM 内部用，不对外暴露
    id = fields.BigIntField(primary_key=True)

    # 软删除标记
    is_deleted = fields.BooleanField(default=False, db_index=True)
    deleted_at = fields.DatetimeField(null=True)

    # 时间戳
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True

    @classmethod
    def all_objects(cls) -> QuerySet:
        """返回包含已假删除行的全量查询集（绕过默认过滤）。"""
        return QuerySet(cls)

    async def soft_delete(self) -> None:
        """业务层「删除」：置 is_deleted 并记录删除时间，绝不物理删除。"""
        from tortoise import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        await self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
