"""pytest 公共 fixture：用 sqlite 内存库，测试不依赖 Postgres。"""

import pytest
import pytest_asyncio
from cryptography.fernet import Fernet
from httpx import ASGITransport, AsyncClient
from tortoise import Tortoise

from app.core.config import settings
from app.main import create_app


@pytest.fixture(autouse=True)
def _test_secrets():
    """为测试注入一个有效的 Fernet 密钥，使 key 加解密可用（不依赖真实 .env）。"""
    original = settings.KEY_ENCRYPTION_SECRET
    settings.KEY_ENCRYPTION_SECRET = Fernet.generate_key().decode()
    yield
    settings.KEY_ENCRYPTION_SECRET = original


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
