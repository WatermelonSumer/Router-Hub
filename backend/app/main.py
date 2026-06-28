"""FastAPI 应用工厂与生命周期。

Web 进程只负责 API；探测 worker 是独立进程（app.worker.scheduler），
两者必须分离（blueprint 架构原则 1：探测慢 IO 不能阻塞用户请求）。
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tortoise import Tortoise

from app.api.router import api_router
from app.core.config import settings
from app.core.db import TORTOISE_ORM


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建立 Tortoise 连接，关闭时释放。

    用 init 而非 generate_schemas：建表交给 aerich 迁移，应用启动不自动改表结构。
    """
    await Tortoise.init(config=TORTOISE_ORM)
    yield
    await Tortoise.close_connections()


def create_app() -> FastAPI:
    """构造 FastAPI 应用实例。"""
    app = FastAPI(
        title=settings.APP_NAME,
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    # CORS：允许前端跨域携带 Authorization 头调用
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
