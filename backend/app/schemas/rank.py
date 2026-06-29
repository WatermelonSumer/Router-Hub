"""排行榜相关 schema。

红线：榜单对游客开放、吃 SEO，但仍只暴露公开安全字段——
绝不含 base_url / key / 站长信息（那些是详情页登录可见或后端内部用）。
"""

from pydantic import BaseModel

# 三大分榜与排序键；非法值由路由层校验
Leaderboard = str  # claude | gpt | gemini
RankSort = str  # composite | speed | uptime


class RankEntry(BaseModel):
    """榜单一行：站点公开信息 + 预计算四项分与综合分。

    分数可能为 null（观察区/预算耗尽时某指标暂无数据，前端标「暂无」，
    绝不显示为 0，见 blueprint 六之二陷阱 C）。
    """

    site_id: str
    name: str
    slug: str
    site_url: str | None
    status: str
    rank: int | None
    composite_score: float | None
    uptime_score: float | None
    speed_score: float | None
    authenticity_score: float | None
    review_score: float | None
    declared_models: list[str] | None


class RankResponse(BaseModel):
    """某分榜的完整结果：主榜 + 观察区试用榜分开返回。

    主榜（online/abnormal/revived）与观察区（observing）刻意分列，
    冷启动新站不污染主榜公信力（blueprint 第七节）。
    """

    leaderboard: str
    sort: str
    main: list[RankEntry]
    observing: list[RankEntry]
