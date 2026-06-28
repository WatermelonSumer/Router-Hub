"""预计算综合分模型（用户查榜直接读这里 / 刷进 Redis ZSET）。"""

from tortoise import fields

from app.models.base import BaseModel, gen_uuid7


class SiteScore(BaseModel):
    """每个站 × 每个分榜一行，Worker 每轮探测后重算。

    四个原始指标各自归一化到 0-100 再加权（算法见 blueprint 六之二）。
    """

    score_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    site_id = fields.UUIDField(db_index=True)  # 虚拟外键 → relay_sites.site_id

    leaderboard = fields.CharField(max_length=16, db_index=True)  # claude | gpt | gemini

    uptime_score = fields.FloatField(null=True)
    speed_score = fields.FloatField(null=True)
    authenticity_score = fields.FloatField(null=True)
    review_score = fields.FloatField(null=True)

    composite_score = fields.FloatField(null=True)
    rank = fields.IntField(null=True)

    class Meta(BaseModel.Meta):
        abstract = False
        table = "site_scores"
