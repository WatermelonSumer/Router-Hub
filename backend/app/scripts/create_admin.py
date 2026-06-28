"""创建（或升级）管理员账号。

用法：
    poetry run python -m app.scripts.create_admin --email admin@example.com
    # 按提示输入密码（隐藏输入，两次确认）

    # 邮箱已存在时，把该用户升级为管理员：
    poetry run python -m app.scripts.create_admin --email someone@example.com --promote

设计：
- 密码不走命令行参数（避免进 shell 历史），用 getpass 隐藏输入。
- admin 角色只能由本脚本产生，注册接口无法创建（见 schemas/auth.py）。
"""

import argparse
import asyncio
import getpass
import sys

from pydantic import EmailStr, TypeAdapter, ValidationError
from tortoise import Tortoise

from app.core.db import TORTOISE_ORM
from app.core.security import hash_password
from app.models.user import User

ADMIN_ROLE = "admin"

# 与登录接口（schemas.auth.LoginRequest）一致的邮箱校验，
# 避免造出"能创建却因邮箱非法登不进去"的账号。
_email_validator = TypeAdapter(EmailStr)


def _validate_email(email: str) -> str | None:
    """校验邮箱合法性；非法返回错误信息，合法返回 None。"""
    try:
        _email_validator.validate_python(email)
        return None
    except ValidationError as exc:
        return exc.errors()[0]["msg"]


def _prompt_password() -> str:
    """隐藏输入密码并二次确认；不满足长度或不一致则重试。"""
    while True:
        pw = getpass.getpass("设置管理员密码（至少 8 位）：")
        if len(pw) < 8:
            print("密码太短，至少 8 位，请重试。\n")
            continue
        pw2 = getpass.getpass("再次输入确认：")
        if pw != pw2:
            print("两次输入不一致，请重试。\n")
            continue
        return pw


async def _run(email: str, promote: bool) -> int:
    """连接数据库并创建/升级管理员，返回进程退出码。"""
    email_err = _validate_email(email)
    if email_err is not None:
        print(f"邮箱不合法：{email_err}")
        return 1

    await Tortoise.init(config=TORTOISE_ORM)
    try:
        existing = await User.filter(email=email).first()

        if existing is not None:
            if existing.role == ADMIN_ROLE:
                print(f"用户 {email} 已经是管理员，无需操作。")
                return 0
            if not promote:
                print(
                    f"邮箱 {email} 已被注册（当前角色：{existing.role}）。\n"
                    f"如需将其升级为管理员，请加 --promote 重新运行。"
                )
                return 1
            existing.role = ADMIN_ROLE
            await existing.save(update_fields=["role", "updated_at"])
            print(f"已将 {email} 升级为管理员（user_id={existing.user_id}）。")
            return 0

        # 新建管理员
        password = _prompt_password()
        admin = await User.create(
            email=email,
            password_hash=hash_password(password),
            role=ADMIN_ROLE,
        )
        print(f"管理员创建成功：{email}（user_id={admin.user_id}）。")
        return 0
    finally:
        await Tortoise.close_connections()


def main() -> None:
    """解析参数并执行。"""
    parser = argparse.ArgumentParser(description="创建或升级管理员账号")
    parser.add_argument("--email", required=True, help="管理员邮箱")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="若邮箱已存在，将该用户升级为管理员",
    )
    args = parser.parse_args()

    exit_code = asyncio.run(_run(args.email, args.promote))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
