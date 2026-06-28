"""全局配置：所有 .env 项集中在 Settings，代码只读 settings，不直接读 os.environ。

阈值清单与默认值对齐 docs/dev/blueprint.md 第十一节。
分榜权重等「需热更新」的配置不在这里，放数据库表 leaderboard_weights。
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从 .env / 环境变量加载的全局配置（带类型校验与默认值）。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 基础
    APP_NAME: str = "Router-Hub"
    DEBUG: bool = False

    # 数据库与缓存
    DATABASE_URL: str = "postgres://postgres:postgres@localhost:5432/router_hub"
    REDIS_URL: str = "redis://localhost:6379/0"

    # 探测频率（秒）
    PROBE_ALIVE_INTERVAL_SEC: int = 300  # 存活探测 5 分钟
    PROBE_QUALITY_INTERVAL_SEC: int = 1800  # 质量探测 30 分钟

    # 状态机阈值（单位：连续探测次数）
    PROBE_FAIL_TO_ABNORMAL: int = 3  # online→abnormal
    PROBE_RECOVER_FROM_ABNORMAL: int = 2  # abnormal→online
    PROBE_FAIL_TO_SUSPECTED: int = 36  # abnormal→suspected_dead (≈3h)
    PROBE_RECOVER_FROM_SUSPECTED: int = 3  # suspected→revived
    PROBE_FAIL_TO_DEAD: int = 576  # suspected→dead (≈48h)
    PROBE_RECOVER_FROM_DEAD: int = 5  # dead→revived
    REVIVED_STABLE_HOURS: int = 24  # revived→online 观察期

    # 冷启动观察区毕业（与条件）
    OBSERVING_MIN_DAYS: int = 7
    OBSERVING_MIN_ALIVE_PROBES: int = 1500
    OBSERVING_MIN_QUALITY_PROBES: int = 48

    # 维护窗上限
    MAINTENANCE_MAX_HOURS_PER_WINDOW: int = 4
    MAINTENANCE_MAX_WINDOWS_PER_WEEK: int = 2

    # 评分归一化
    UPTIME_HALFLIFE_DAYS: float = 7.0  # 在线率时间衰减半衰期
    SPEED_ANCHORS_MS: str = "1500,3000,6000,10000"  # 速度映射拐点（毫秒）
    SPEED_ANCHORS_SCORE: str = "100,75,50,20"  # 拐点对应分数
    AUTHENTICITY_WINDOW: int = 20  # 真实性取最近 N 次质量探测
    REVIEW_BAYESIAN_C: int = 5  # 评价贝叶斯置信常数（虚拟评价数）

    # 安全（绝不进库/日志）
    KEY_ENCRYPTION_SECRET: str = ""  # Fernet 密钥；生产必须经 .env 注入
    JWT_SECRET: str = "dev-insecure-change-me-please-use-32+bytes"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 访问令牌有效期，默认 7 天

    @property
    def speed_anchors_ms(self) -> list[int]:
        """速度锚点（毫秒）解析为有序整数列表。"""
        return [int(x) for x in self.SPEED_ANCHORS_MS.split(",")]

    @property
    def speed_anchors_score(self) -> list[float]:
        """速度锚点对应分数解析为浮点列表。"""
        return [float(x) for x in self.SPEED_ANCHORS_SCORE.split(",")]


@lru_cache
def get_settings() -> Settings:
    """单例配置：进程内只构造一次。"""
    return Settings()


settings = get_settings()
