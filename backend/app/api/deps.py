"""FastAPI 依赖注入：从 Bearer 令牌解析当前用户。

token 校验失败、用户不存在均抛 401，错误信息不区分具体原因（防探测）。
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.models.user import User

# auto_error=False：缺失令牌时由本依赖统一抛 401，错误格式可控
_bearer = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="未认证或令牌无效",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> User:
    """解析 Authorization: Bearer <token>，返回当前登录用户。"""
    if credentials is None or not credentials.credentials:
        raise _UNAUTHORIZED

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise _UNAUTHORIZED from exc

    user_id = payload.get("sub")
    if not user_id:
        raise _UNAUTHORIZED

    user = await User.filter(user_id=user_id).first()
    if user is None:
        raise _UNAUTHORIZED
    return user
