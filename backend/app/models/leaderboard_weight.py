"""分榜权重模型：每个分榜一套权重，可热更新（不写死在代码）。"""

from tortoise import fields

from app.models.base import BaseModel, gen_uuid7


class LeaderboardWeight(BaseModel):
    """每个分榜一套权重。

    三榜取向不同：Claude 榜抬高真实性；GPT 榜抬高价格/在线率；Gemini 榜抬高在线率。
    """

    weight_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    leaderboard = fields.CharField(max_length=16, db_index=True)  # claude | gpt | gemini

    w_uptime = fields.FloatField(default=0.0)
    w_speed = fields.FloatField(default=0.0)
    w_authenticity = fields.FloatField(default=0.0)
    w_review = fields.FloatField(default=0.0)

    class Meta(BaseModel.Meta):
        abstract = False
        table = "leaderboard_weights"
