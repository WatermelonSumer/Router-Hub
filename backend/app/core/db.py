"""Tortoise ORM 与 Aerich 共用的连接配置。

aerich 的 [tool.aerich] tortoise_orm 指向本模块的 TORTOISE_ORM。
模型全部在 app.models 汇总导入，便于 Tortoise/aerich 发现。
"""

from app.core.config import settings

TORTOISE_ORM = {
    "connections": {"default": settings.DATABASE_URL},
    "apps": {
        "models": {
            # aerich.models 必须包含，否则迁移表 aerich 不会被建
            "models": ["app.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    # 时间统一用 UTC，展示层再转时区
    "use_tz": True,
    "timezone": "UTC",
}
