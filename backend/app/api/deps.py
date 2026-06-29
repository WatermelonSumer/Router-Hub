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


async def get_current_owner(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为站长（owner）；否则 403。

    管理员（admin）不自动具备站长身份：上架是站长的业务动作，
    需要时由管理员单独的接口操作，避免角色语义混淆。
    """
    if current_user.role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅站长可执行此操作",
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为管理员（admin）；否则 403。

    admin 只能由脚本创建（注册接口造不出），用于站点审核等平台运营动作。
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可执行此操作",
        )
    return current_user


async def get_owner_or_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """要求当前用户为站长或管理员；否则 403。

    用于集市只读浏览/内容下架等动作：站长是交易方，admin 是监管方，
    两者都可读；但发帖/对接等交易动作仍只限站长（用 get_current_owner）。
    """
    if current_user.role not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅站长或管理员可执行此操作",
        )
    return current_user
