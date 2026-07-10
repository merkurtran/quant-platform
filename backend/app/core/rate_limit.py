"""基于 Redis 的滑动窗口速率限制器（Lua 脚本保证原子性）"""
import logging

from fastapi import Request, HTTPException, status
from shared.redis_client import get_redis_client

logger = logging.getLogger(__name__)

# Lua 脚本：incr + expire 原子操作，消除竞态窗口
# 返回值: 当前计数（首次调用返回 1）
_RATE_LIMIT_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return current
"""


def _get_client_ip(request: Request) -> str:
    """优先取 X-Forwarded-For 最左侧 IP，其次取直连 IP"""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limiter(max_requests: int = 5, window_seconds: int = 60):
    """
    返回一个 FastAPI dependency，基于请求 IP 限流。

    Args:
        max_requests: 时间窗口内最大请求数
        window_seconds: 时间窗口秒数
    """
    def _limiter(request: Request):
        client_ip = _get_client_ip(request)
        key = f"rate_limit:{request.url.path}:{client_ip}"

        r = get_redis_client()
        try:
            current = r.eval(_RATE_LIMIT_SCRIPT, 1, key, window_seconds)
        except Exception as e:
            logger.warning(f"Rate limit check failed, allowing request: {e}")
            # Redis 故障时放行（fail-open），避免阻断正常业务
            current = 0

        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please try again later",
                headers={"Retry-After": str(window_seconds)},
            )

    return _limiter
