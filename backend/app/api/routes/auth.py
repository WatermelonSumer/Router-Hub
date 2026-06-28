"""认证路由：注册、登录、获取当前用户。

token 只装载 user_id（业务键）；响应绝不含 password_hash。
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UserPublic,
)
from app.services.auth_service import (
    EmailAlreadyExists,
    InvalidCredentials,
    authenticate_user,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _to_token_response(user: User) -> TokenResponse:
    """根据用户签发令牌并组装响应。"""
    token = create_access_token(subject=str(user.user_id))
    return TokenResponse(
        access_token=token,
        user=UserPublic(
            user_id=str(user.user_id),
            email=user.email,
            role=user.role,  # type: ignore[arg-type]
        ),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest) -> TokenResponse:
    """注册新用户（user|owner），成功后直接返回登录令牌。"""
    try:
        user = await register_user(data)
    except EmailAlreadyExists as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已被注册",
        ) from exc
    return _to_token_response(user)


@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest) -> TokenResponse:
    """邮箱 + 密码登录。"""
    try:
        user = await authenticate_user(data.email, data.password)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        ) from exc
    return _to_token_response(user)


@router.get("/me", response_model=UserPublic)
async def me(current_user: User = Depends(get_current_user)) -> UserPublic:
    """返回当前登录用户的公开信息。"""
    return UserPublic(
        user_id=str(current_user.user_id),
        email=current_user.email,
        role=current_user.role,  # type: ignore[arg-type]
    )
