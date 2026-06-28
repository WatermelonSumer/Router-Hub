"""认证相关的请求/响应 schema。

注册时区分 role（user|owner）；站长（owner）必填微信 + QQ 联系方式
（红线：联系方式默认隐藏，仅对接 confirmed 后交换，但注册必填以便平台可触达）。
"""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator

# 系统内全部角色：admin 只能由脚本创建，注册接口无法产生
Role = Literal["user", "owner", "admin"]
# 注册时允许的角色：刻意不含 admin，防止外部注册出管理员
RegisterRole = Literal["user", "owner"]


class RegisterRequest(BaseModel):
    """注册请求。"""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: RegisterRole = "user"
    wechat: str | None = Field(default=None, max_length=128)
    qq: str | None = Field(default=None, max_length=32)

    @model_validator(mode="after")
    def _owner_requires_contact(self) -> "RegisterRequest":
        """站长必须提供微信和 QQ；普通用户不强制。"""
        if self.role == "owner" and (not self.wechat or not self.qq):
            raise ValueError("站长注册必须填写微信和 QQ 联系方式")
        return self


class LoginRequest(BaseModel):
    """登录请求。"""

    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserPublic(BaseModel):
    """对外暴露的用户信息（绝不含 password_hash；联系方式默认不下发）。"""

    user_id: str
    email: EmailStr
    role: Role


class TokenResponse(BaseModel):
    """登录/注册成功返回的令牌与用户信息。"""

    access_token: str
    token_type: str = "bearer"
    user: UserPublic
