"""基于 Redis 的简单速率限制器"""
from fastapi import Request, HTTPException, status
from shared.redis_client import redis_client


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

        r = redis_client
        current = r.incr(key)
        if current == 1:
            r.expire(key, window_seconds)

        if current > max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests, please try again later",
            )

    return _limiter
