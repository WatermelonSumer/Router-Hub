"""模型汇总导入：供 Tortoise / Aerich 发现全部表。

新增模型时务必在此处导入并加入 __all__，否则不会被建表。
"""

from app.models.leaderboard_weight import LeaderboardWeight
from app.models.marketplace_post import MarketplacePost
from app.models.post_response import PostResponse
from app.models.probe_result import ProbeResult
from app.models.relay_site import RelaySite
from app.models.review import Review
from app.models.site_score import SiteScore
from app.models.user import User

__all__ = [
    "User",
    "RelaySite",
    "ProbeResult",
    "SiteScore",
    "LeaderboardWeight",
    "Review",
    "MarketplacePost",
    "PostResponse",
]
