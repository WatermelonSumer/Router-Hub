"""中转站模型：站长上架的站点，含探测/坟场/冷启动统一状态机。"""

from tortoise import fields

from app.models.base import BaseModel, SoftDeleteManager, gen_uuid7


class RelaySite(BaseModel):
    """站长上架的中转站。

    status 是统管三件事的状态机：
    - 审核：pending
    - 冷启动观察区：observing（满样本 + 满 7 天转 online）
    - 坟场分级：online → abnormal → suspected_dead → dead → revived
    """

    site_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    owner_id = fields.UUIDField(db_index=True)  # 虚拟外键 → users.user_id

    name = fields.CharField(max_length=128)
    slug = fields.CharField(max_length=128)  # URL 用，永不改；唯一走 partial unique index
    site_url = fields.CharField(max_length=512, null=True)
    base_url = fields.CharField(max_length=512)

    # key 加密落库，永不下发前端；站长本人只见 key_hint 掩码
    encrypted_key = fields.TextField()
    key_hint = fields.CharField(max_length=32)  # 形如 sk-***1234

    probe_budget_daily = fields.IntField(default=0)  # 站长每日质量探测预算上限，超额降频

    declared_models = fields.JSONField(null=True)  # 站长声称支持的模型清单

    # 决策硬信息：详情页对游客锁，登录可见
    min_topup = fields.DecimalField(max_digits=12, decimal_places=2, null=True)
    pay_methods = fields.CharField(max_length=256, null=True)
    rpm_limit = fields.IntField(null=True)

    status = fields.CharField(max_length=24, default="pending", db_index=True)

    maintenance_windows = fields.JSONField(null=True)  # 站长声明的维护窗，窗内失败不计在线率

    first_seen_at = fields.DatetimeField(null=True)
    last_probe_at = fields.DatetimeField(null=True)

    class Meta:
        table = "relay_sites"
        manager = SoftDeleteManager()
