"""探测时序结果模型（会膨胀，后期分区/降采样）。"""

from tortoise import fields

from app.models.base import BaseModel, gen_uuid7


class ProbeResult(BaseModel):
    """单次探测结果。

    probe_type：alive（存活探测）| quality（质量探测）| triggered（异常触发探测）。
    is_authentic：MVP 真实性只做「通了/没通」0/1，降智检测留长期。
    """

    probe_id = fields.UUIDField(default=gen_uuid7, unique=True, db_index=True)
    site_id = fields.UUIDField(db_index=True)  # 虚拟外键 → relay_sites.site_id

    probe_type = fields.CharField(max_length=16, db_index=True)  # alive | quality | triggered
    probed_at = fields.DatetimeField(db_index=True)

    target_model = fields.CharField(max_length=128, null=True)
    ttfb_ms = fields.IntField(null=True)
    total_ms = fields.IntField(null=True)
    http_status = fields.IntField(null=True)

    is_alive = fields.BooleanField(default=False)
    is_authentic = fields.BooleanField(null=True)  # 0/1，质量探测才有

    error_sample = fields.TextField(null=True)

    class Meta(BaseModel.Meta):
        abstract = False
        table = "probe_results"
