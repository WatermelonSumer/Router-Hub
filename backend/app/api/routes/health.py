"""健康检查路由。"""

from fastapi import APIRouter
from tortoise import connections

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """健康检查：进程存活 + 数据库可达。

    数据库 ping 失败时 db 字段返回 down，但整体仍返回 200，
    便于区分「进程挂了」与「DB 暂时不可达」。
    """
    db_ok = False
    try:
        conn = connections.get("default")
        await conn.execute_query("SELECT 1")
        db_ok = True
    except Exception:
        db_ok = False

    return {"status": "ok", "db": "up" if db_ok else "down"}
