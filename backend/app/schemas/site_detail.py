"""站点详情页相关 schema（C 端，吃 SEO）。

详情页分三屏（features.md 第 4 节）：
- 信任卡（游客可见）：状态/存活时长/最近探测/30 天在线率曲线/已验证可用。
- 性能区（部分锁登录）：模型清单（游客）+ 实测延迟（登录）。
- 决策区（锁登录）：起充门槛/支付方式/限速/跳转。

红线：公开层与登录层【都】绝不含 base_url / encrypted_key / key_hint——
那些是 worker 内部用，永不下发前端（security-and-business-constraints）。
"""

from decimal import Decimal

from pydantic import BaseModel


class UptimePoint(BaseModel):
    """在线率曲线的一个数据点：某一天的在线率（0-100）。

    uptime 为 None 表示当天无探测样本（前端断点，不画成 0）。
    """

    date: str  # YYYY-MM-DD
    uptime: float | None


class SiteScoreBrief(BaseModel):
    """该站在某分榜的预计算分摘要（详情页信任卡展示用）。"""

    leaderboard: str
    composite_score: float | None
    rank: int | None


class SitePublicView(BaseModel):
    """游客可见的站点详情：用于 SSR，吃 SEO。

    绝不含硬信息（价格/起充/限速/延迟）与 key/base_url。
    """

    site_id: str
    name: str
    slug: str
    site_url: str | None  # 对外主页（与榜单一致公开；跳转转化仍靠登录后硬信息）
    status: str
    declared_models: list[str] | None

    first_seen_at: str | None  # 最早被探测到的时刻
    listed_at: str  # 上架时间（created_at）
    last_probe_at: str | None  # 最近一次探测时间戳（「数据是活的」公信力）
    status_changed_at: str | None  # 进入当前状态的时刻（坟场计时/「曾阵亡 X 天」起点）

    verified: bool  # MVP：是否有过成功的质量探测（真打通 chat）→「已验证可用✓」

    uptime_30d: float | None  # 近 30 天总在线率（无样本则 None）
    uptime_history: list[UptimePoint]  # 近 30 天逐日在线率曲线

    scores: list[SiteScoreBrief]  # 该站在各分榜的综合分/名次


class SiteGatedView(BaseModel):
    """登录后可见的硬信息：决策区 + 实测延迟。

    红线：仍绝不含 key/base_url；这里只放对登录用户开放的决策硬信息。
    """

    site_id: str
    slug: str
    min_topup: Decimal | None
    pay_methods: str | None
    rpm_limit: int | None

    ttfb_p50_ms: int | None  # 质量探测 TTFB 中位数
    ttfb_p90_ms: int | None  # 质量探测 TTFB P90
    latency_samples: int  # 参与统计的质量探测样本数
