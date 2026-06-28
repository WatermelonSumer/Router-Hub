"""安全相关工具：站长 key 加密、密码哈希。

红线约束（见 docs/dev、项目记忆 security-and-business-constraints）：
- 站长 key 加密落库，永不下发前端，绝不进日志。
- 加密密钥仅来自 .env（KEY_ENCRYPTION_SECRET），不进代码库。
"""

import bcrypt
from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    """构造 Fernet 实例；密钥缺失时立即报错，避免静默使用空密钥。"""
    secret = settings.KEY_ENCRYPTION_SECRET
    if not secret:
        raise RuntimeError("KEY_ENCRYPTION_SECRET 未配置，无法加解密站长 key")
    return Fernet(secret.encode())


def encrypt_key(plaintext: str) -> str:
    """加密站长 API key，返回可落库的密文字符串。"""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    """解密站长 API key，仅在后端 worker 内调用，结果绝不下发前端/进日志。"""
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    """生成展示用掩码（如 sk-***1234），站长本人也只见这个。"""
    if len(plaintext) <= 7:
        return "sk-***"
    return f"{plaintext[:3]}***{plaintext[-4:]}"


def hash_password(password: str) -> str:
    """对用户密码做 bcrypt 哈希。

    bcrypt 上限 72 字节，超长部分会被忽略，这里显式截断以保证行为可预期。
    """
    pw = password.encode("utf-8")[:72]
    return bcrypt.hashpw(pw, bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """校验明文密码与哈希是否匹配。"""
    pw = password.encode("utf-8")[:72]
    return bcrypt.checkpw(pw, password_hash.encode("utf-8"))
