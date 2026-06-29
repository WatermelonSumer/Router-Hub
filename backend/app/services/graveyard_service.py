"""坟场读取业务逻辑：只读筛坟场态站点，分流疑似/已阵亡。

只读 relay_sites，绝不在此算分（坟场站不上榜）。仿 rank_service 只读模式。
红线：返回的数据载体绝不携带 base_url / encrypted_key / key_hint。
"""

from app.models.relay_site import RelaySite

# 坟场两态：疑似跑路 / 已确认阵亡
_SUSPECTED = "suspected_dead"
_DEAD = "dead"


class GraveyardEntryData:
    """坟场一行的数据载体（站点公开信息），供路由层转 schema。"""

    def __init__(self, site: RelaySite):
        self.site_id = str(site.site_id)
        self.name = site.name
        self.slug = site.slug
        self.site_url = site.site_url
        self.status = site.status
        self.declared_models = site.declared_models
        self.first_seen_at = site.first_seen_at
        self.last_probe_at = site.last_probe_at
        self.status_changed_at = site.status_changed_at


async def list_graveyard() -> tuple[list[GraveyardEntryData], list[GraveyardEntryData]]:
    """返回 (疑似跑路, 已确认阵亡) 两个列表。

    按 status_changed_at 倒序——最近进入坟场的置顶（最有传播性）；
    缺该时间戳的垫底。
    """
    sites = await RelaySite.filter(status__in=[_SUSPECTED, _DEAD]).order_by(
        "-status_changed_at", "-created_at"
    )
    suspected: list[GraveyardEntryData] = []
    dead: list[GraveyardEntryData] = []
    for site in sites:
        entry = GraveyardEntryData(site)
        if site.status == _SUSPECTED:
            suspected.append(entry)
        else:
            dead.append(entry)
    return suspected, dead
