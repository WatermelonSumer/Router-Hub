"""中转站上架相关 schema。

红线：请求里的 api_key 加密落库后即丢弃，任何响应都绝不回传明文 key /
密文，只回传掩码 key_hint（见 services/site_service、core/security）。
"""

from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

# 站长可声明的模型家族（用于分榜归类，校验非空时用）
ModelFamily = str


class SiteCreateRequest(BaseModel):
    """站长上架中转站的请求。"""

    name: str = Field(min_length=2, max_length=128)
    base_url: str = Field(min_length=1, max_length=512, description="探测用的 API 基址")
    api_key: str = Field(min_length=1, max_length=512, description="探测用 key，加密落库")

    # 可选：不传则由后端按 name 生成
    slug: str | None = Field(default=None, max_length=128)
    site_url: str | None = Field(default=None, max_length=512, description="对外展示主页")

    declared_models: list[str] | None = Field(default=None, description="声称支持的模型清单")
    min_topup: Decimal | None = Field(default=None, ge=0)
    pay_methods: str | None = Field(default=None, max_length=256)
    rpm_limit: int | None = Field(default=None, ge=0)

    @field_validator("slug")
    @classmethod
    def _slug_charset(cls, v: str | None) -> str | None:
        """slug 仅允许小写字母、数字、连字符。"""
        if v is None:
            return v
        v = v.strip().lower()
        if not v:
            return None
        if not all(c.isalnum() or c == "-" for c in v):
            raise ValueError("slug 只能包含字母、数字和连字符")
        return v


class SiteOwnerView(BaseModel):
    """站长视角的站点信息：含 key_hint 与状态，绝不含明文/密文 key。"""

    site_id: str
    name: str
    slug: str
    base_url: str
    site_url: str | None
    key_hint: str
    status: str
    declared_models: list[str] | None
    min_topup: Decimal | None
    pay_methods: str | None
    rpm_limit: int | None
