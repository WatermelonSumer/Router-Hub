"""认证业务逻辑：注册、登录校验。

用自定义异常表达业务错误，由路由层翻译成 HTTP 状态码，
保持 service 层不依赖 FastAPI。
"""

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import RegisterRequest


class AuthError(Exception):
    """认证相关业务错误基类。"""


class EmailAlreadyExists(AuthError):
    """邮箱已被注册（仅统计未假删除的用户）。"""


class InvalidCredentials(AuthError):
    """邮箱不存在或密码错误（统一错误，避免泄露邮箱是否注册）。"""


async def register_user(data: RegisterRequest) -> User:
    """注册新用户：邮箱查重 → 密码哈希 → 建用户。

    查重只看未假删除的记录（默认管理器已过滤 is_deleted）；
    邮箱唯一性最终由数据库 partial unique index 兜底（见迁移）。
    """
    existing = await User.filter(email=data.email).first()
    if existing is not None:
        raise EmailAlreadyExists(data.email)

    user = await User.create(
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
        wechat=data.wechat,
        qq=data.qq,
    )
    return user


async def authenticate_user(email: str, password: str) -> User:
    """校验邮箱 + 密码，成功返回用户，失败抛 InvalidCredentials。"""
    user = await User.filter(email=email).first()
    if user is None or not verify_password(password, user.password_hash):
        raise InvalidCredentials(email)
    return user
