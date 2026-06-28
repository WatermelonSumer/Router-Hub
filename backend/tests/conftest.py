"""pytest 公共 fixture：用 sqlite 内存库，测试不依赖 Postgres。"""

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.main import create_app


@pytest_asyncio.fixture
async def client():
    """初始化 sqlite 内存库 + 建表，提供异步测试客户端，结束后清理。

    httpx 的 ASGITransport 不触发 FastAPI lifespan（即不会连 Postgres），
    因此这里手动用 sqlite 内存库初始化 Tortoise 并建表，测试无需外部依赖。
    """
    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models"]},
    )
    await Tortoise.generate_schemas()

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    await Tortoise.close_connections()
