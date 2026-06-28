"""探测调度器：独立进程，APScheduler 起三周期 job。

入口：python -m app.worker.scheduler
与 web 进程分离，避免慢 IO/上游限速阻塞用户请求。
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from tortoise import Tortoise

from app.core.config import settings
from app.core.db import TORTOISE_ORM
from app.worker.probes import run_alive_probe, run_quality_probe

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("router_hub.worker")


def build_scheduler() -> AsyncIOScheduler:
    """注册存活/质量两个周期 job（触发探测由存活探测内部按需插队）。"""
    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_alive_probe,
        "interval",
        seconds=settings.PROBE_ALIVE_INTERVAL_SEC,
        id="alive_probe",
    )
    scheduler.add_job(
        run_quality_probe,
        "interval",
        seconds=settings.PROBE_QUALITY_INTERVAL_SEC,
        id="quality_probe",
    )
    return scheduler


async def main() -> None:
    """启动 Tortoise 连接与调度器，常驻运行。"""
    await Tortoise.init(config=TORTOISE_ORM)
    scheduler = build_scheduler()
    scheduler.start()
    logger.info(
        "探测调度器已启动：alive=%ss quality=%ss",
        settings.PROBE_ALIVE_INTERVAL_SEC,
        settings.PROBE_QUALITY_INTERVAL_SEC,
    )
    try:
        # 常驻：阻塞在一个永不结束的事件上，让调度器持续运行
        await asyncio.Event().wait()
    finally:
        scheduler.shutdown()
        await Tortoise.close_connections()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("探测调度器已停止")
