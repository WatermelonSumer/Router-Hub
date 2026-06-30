"""C 端充值验证适配层。

用户提交自己在目标站点的 key 后，后端只用它做一次额度/用量查询，
不落库、不回传、不写日志。不同 new-api/sub2api 版本的额度接口不完全一致，
因此这里集中维护探测顺序，业务层只关心是否验证通过。
"""

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Protocol

import httpx


class TopupVerifier(Protocol):
    """充值验证器协议，便于测试注入假实现。"""

    async def verify(self, *, base_url: str, api_key: str) -> bool:
        """返回该 key 是否能证明用户在目标站有过充值/用量。"""


class HttpTopupVerifier:
    """通过常见额度/用量接口验证用户 key。

    base_url 通常是 OpenAI 兼容入口（可能带 /v1），额度接口往往在站点根路径；
    因此会同时尝试原始 base 和去掉 /v1 后的根路径。
    """

    _ENDPOINTS = (
        "/dashboard/billing/usage",
        "/dashboard/billing/credit_grants",
        "/api/user/self",
    )
    _POSITIVE_KEYS = {
        "total_usage",
        "used_quota",
        "quota_used",
        "used",
        "total_used",
        "available_grant_amount",
        "total_granted",
        "balance",
        "quota",
        "remain_quota",
    }

    def __init__(self, *, timeout: float = 8.0) -> None:
        self._timeout = timeout

    async def verify(self, *, base_url: str, api_key: str) -> bool:
        """尝试多个常见接口；任一接口返回正向额度/用量即视为 verified。"""
        headers = {"Authorization": f"Bearer {api_key}"}
        async with httpx.AsyncClient(timeout=self._timeout, headers=headers) as client:
            for base in _candidate_bases(base_url):
                for endpoint in self._ENDPOINTS:
                    url = base.rstrip("/") + endpoint
                    if await self._verify_url(client, url):
                        return True
        return False

    async def _verify_url(self, client: httpx.AsyncClient, url: str) -> bool:
        try:
            resp = await client.get(url)
        except httpx.HTTPError:
            return False
        if resp.status_code in (401, 403):
            return False
        if resp.status_code >= 400:
            return False
        try:
            payload = resp.json()
        except ValueError:
            return False
        return _contains_positive_metric(payload)


def _candidate_bases(base_url: str) -> list[str]:
    """生成可能的站点根路径，避免把 /v1 误拼到管理接口前。"""
    raw = base_url.rstrip("/")
    bases = [raw]
    if raw.endswith("/v1"):
        bases.append(raw[: -len("/v1")])
    return list(dict.fromkeys(bases))


def _contains_positive_metric(value: Any) -> bool:
    """递归查找常见额度/用量字段，只要有正数就通过验证。"""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key) in HttpTopupVerifier._POSITIVE_KEYS and _is_positive(item):
                return True
            if _contains_positive_metric(item):
                return True
    if isinstance(value, list):
        return any(_contains_positive_metric(item) for item in value)
    return False


def _is_positive(value: Any) -> bool:
    try:
        return Decimal(str(value)) > 0
    except (InvalidOperation, TypeError, ValueError):
        return False
