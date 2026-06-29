"""底层 HTTP 探测：打中转站的 OpenAI 兼容接口，返回结构化结果。

设计：
- client 由调用方注入（httpx.AsyncClient），便于测试用 MockTransport 替身。
- 纯 HTTP，不碰数据库。
- 红线：质量探测要用站长 key，但 key 绝不进 error_sample / 日志 / 返回值。
- 防作弊：随机 UA + 轻随机 prompt，抬高站长「给探测开小灶」的门槛
  （blueprint 第五节防作弊小成本措施）。
"""

import random
import time
from dataclasses import dataclass

import httpx

# 随机 UA 池：不固定 UA，避免站长识别探测流量
_UA_POOL = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "python-requests/2.32",
    "okhttp/4.12.0",
)

# 轻随机 prompt 池：质量探测每次换一个，避免被预设缓存命中
_PROMPT_POOL = (
    "ping",
    "hi",
    "say ok",
    "1+1=?",
    "respond with a word",
)

# 探测超时（秒）：存活探测要快，质量探测留足上游生成首 token 的时间
_ALIVE_TIMEOUT = 10.0
_QUALITY_TIMEOUT = 30.0


@dataclass
class AliveOutcome:
    """存活探测结果。"""

    is_alive: bool
    ttfb_ms: int | None
    total_ms: int | None
    http_status: int | None
    error_sample: str | None = None


@dataclass
class QualityOutcome:
    """质量探测结果。"""

    is_alive: bool
    is_authentic: bool
    ttfb_ms: int | None
    total_ms: int | None
    http_status: int | None
    target_model: str | None = None
    error_sample: str | None = None


def _rand_headers(extra: dict | None = None) -> dict:
    """构造带随机 UA 的请求头。"""
    headers = {"User-Agent": random.choice(_UA_POOL)}
    if extra:
        headers.update(extra)
    return headers


def _join(base_url: str, path: str) -> str:
    """安全拼接 base_url 与路径（base_url 可能已带或不带尾斜杠）。"""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


async def probe_alive(client: httpx.AsyncClient, base_url: str) -> AliveOutcome:
    """存活探测：GET /v1/models。

    通了（2xx）即视为存活；超时/连接错误/非 2xx 均视为未存活。
    """
    url = _join(base_url, "v1/models")
    start = time.monotonic()
    try:
        resp = await client.get(url, headers=_rand_headers(), timeout=_ALIVE_TIMEOUT)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        alive = 200 <= resp.status_code < 300
        return AliveOutcome(
            is_alive=alive,
            ttfb_ms=elapsed_ms,
            total_ms=elapsed_ms,
            http_status=resp.status_code,
            error_sample=None if alive else f"非 2xx：{resp.status_code}",
        )
    except httpx.TimeoutException:
        return AliveOutcome(False, None, None, None, error_sample="超时")
    except httpx.HTTPError as exc:
        # 只记异常类型，绝不记 url 查询串等可能含敏感信息的内容
        return AliveOutcome(False, None, None, None, error_sample=f"连接错误：{type(exc).__name__}")


def _looks_authentic(data: dict) -> bool:
    """判定 chat 响应是否像真实模型回复（MVP 只做 0/1）。

    要求响应体含非空 choices 且首条带文本内容。返回假模型/空壳的站不通过。
    """
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return False
    first = choices[0]
    if not isinstance(first, dict):
        return False
    message = first.get("message")
    if isinstance(message, dict) and message.get("content"):
        return True
    # 兼容流式/老格式的 text 字段
    return bool(first.get("text"))


async def probe_quality(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
    model: str,
) -> QualityOutcome:
    """质量探测：用站长 key 打 POST /v1/chat/completions（最短 prompt）。

    红线：api_key 仅用于本次请求头，绝不写入返回值 / error_sample / 日志。
    """
    url = _join(base_url, "v1/chat/completions")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": random.choice(_PROMPT_POOL)}],
        "max_tokens": 1,
    }
    headers = _rand_headers({"Authorization": f"Bearer {api_key}"})
    start = time.monotonic()
    try:
        resp = await client.post(url, json=payload, headers=headers, timeout=_QUALITY_TIMEOUT)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        alive = 200 <= resp.status_code < 300
        if not alive:
            return QualityOutcome(
                is_alive=False,
                is_authentic=False,
                ttfb_ms=elapsed_ms,
                total_ms=elapsed_ms,
                http_status=resp.status_code,
                target_model=model,
                error_sample=f"非 2xx：{resp.status_code}",
            )
        try:
            authentic = _looks_authentic(resp.json())
        except ValueError:
            authentic = False
        return QualityOutcome(
            is_alive=True,
            is_authentic=authentic,
            ttfb_ms=elapsed_ms,
            total_ms=elapsed_ms,
            http_status=resp.status_code,
            target_model=model,
            error_sample=None if authentic else "响应不含有效模型回复",
        )
    except httpx.TimeoutException:
        return QualityOutcome(False, False, None, None, None, model, "超时")
    except httpx.HTTPError as exc:
        return QualityOutcome(
            False, False, None, None, None, model, f"连接错误：{type(exc).__name__}"
        )
