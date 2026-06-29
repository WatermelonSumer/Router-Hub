"""排行榜读取业务逻辑：读预计算分 + 关联站点，分流主榜/观察区。

只读 site_scores（预计算结果）与 relay_sites，绝不在此计算分数——
分数计算是探测 worker 的职责（blueprint 第五/六节）。
"""

from app.models.relay_site import RelaySite
from app.models.site_score import SiteScore

# 合法分榜与排序键
VALID_LEADERBOARDS = ("claude", "gpt", "gemini")
VALID_SORTS = ("composite", "speed", "uptime")

# 主榜展示的站点状态：在线 + 抖动(abnormal,标黄仍在榜) + 复活
_MAIN_STATUSES = ("online", "abnormal", "revived")
# 观察区：冷启动新站
_OBSERVING_STATUS = "observing"


class RankEntryData:
    """榜单一行的数据载体（score + 站点公开信息），供路由层转 schema。"""

    def __init__(self, score: SiteScore, site: RelaySite):
        self.site_id = str(site.site_id)
        self.name = site.name
        self.slug = site.slug
        self.site_url = site.site_url
        self.status = site.status
        self.rank = score.rank
        self.composite_score = score.composite_score
        self.uptime_score = score.uptime_score
        self.speed_score = score.speed_score
        self.authenticity_score = score.authenticity_score
        self.review_score = score.review_score
        self.declared_models = site.declared_models


def _sort_key(entry: RankEntryData, sort: str) -> float:
    """取排序值；None 垫底（视为 -1，保证有数据的排在前）。"""
    field = {
        "composite": entry.composite_score,
        "speed": entry.speed_score,
        "uptime": entry.uptime_score,
    }[sort]
    return field if field is not None else -1.0


async def get_rankings(
    leaderboard: str, sort: str = "composite"
) -> tuple[list[RankEntryData], list[RankEntryData]]:
    """返回 (主榜, 观察区) 两个已排序列表。

    按 leaderboard 过滤 site_scores，service 层关联 relay_sites 拿状态/名称，
    按站点 status 分流；坟场状态（suspected_dead/dead）不上任何榜。
    """
    scores = await SiteScore.filter(leaderboard=leaderboard)
    if not scores:
        return [], []

    site_ids = {s.site_id for s in scores}
    sites = await RelaySite.filter(site_id__in=list(site_ids))
    site_map = {str(s.site_id): s for s in sites}

    main: list[RankEntryData] = []
    observing: list[RankEntryData] = []
    for score in scores:
        site = site_map.get(str(score.site_id))
        if site is None:  # 站点已假删除等：跳过
            continue
        entry = RankEntryData(score, site)
        if site.status in _MAIN_STATUSES:
            main.append(entry)
        elif site.status == _OBSERVING_STATUS:
            observing.append(entry)
        # 其余状态（pending/suspected_dead/dead）不上榜

    main.sort(key=lambda e: _sort_key(e, sort), reverse=True)
    observing.sort(key=lambda e: _sort_key(e, sort), reverse=True)
    return main, observing
