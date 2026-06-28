"""聚合路由：把各业务子路由挂到一起。

后续 auth/rank/sites/reviews/graveyard/market/admin 路由在此注册。
"""

from fastapi import APIRouter

from app.api.routes import auth, health, sites

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(sites.router)
