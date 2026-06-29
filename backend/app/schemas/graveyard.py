"""中转站坟场相关 schema（C 端，吃 SEO，传播引爆点）。

红线（features.md 第 5 节）：全程客观探测事实措辞，绝不主观定性；
只暴露公开安全字段，绝不含 base_url / key / 站长信息。
"""

from pydantic import BaseModel


class GraveyardEntry(BaseModel):
    """坟场一行：阵亡/疑似阵亡站点的公开信息。

    不含分数（坟场不上榜）；status_changed_at 是进入当前坟场状态的时刻，
    前端据此算「连续探测失败 N 天」（客观事实）。
    """

    site_id: str
    name: str
    slug: str
    site_url: str | None
    status: str  # suspected_dead | dead
    declared_models: list[str] | None
    first_seen_at: str | None  # 最早被探测到（「活过多久」）
    last_probe_at: str | None  # 最近一次探测时间戳
    status_changed_at: str | None  # 进入坟场状态时刻（失败计时起点）


class GraveyardResponse(BaseModel):
    """坟场完整结果：疑似跑路 + 已确认阵亡分列两区。

    分区刻意区分「疑似 vs 坐实」，防误伤、措辞分级（features.md 第 5 节）。
    """

    suspected: list[GraveyardEntry]  # suspected_dead
    dead: list[GraveyardEntry]  # dead
