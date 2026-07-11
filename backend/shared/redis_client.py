import redis
import redis.asyncio as redis_asyncio

from app.core.config import get_settings

# 显式模块导出（替代 __getattr__ 动态代理，使 mypy/pyright 可做完整类型推断）
__all__ = [
    "get_redis_client",
    "get_async_redis_client",
]

_redis_client: redis.Redis | None = None
_async_redis_client: redis_asyncio.Redis | None = None


def get_redis_client() -> redis.Redis:
    """同步 Redis 客户端,懒加载,首次调用时连接。"""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = redis.Redis.from_url(
            settings.redis.url,
            decode_responses=True,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis_client


def get_async_redis_client() -> redis_asyncio.Redis:
    """异步 Redis 客户端,懒加载,首次调用时连接。"""
    global _async_redis_client
    if _async_redis_client is None:
        settings = get_settings()
        _async_redis_client = redis_asyncio.from_url(
            settings.redis.url,
            decode_responses=True,
            socket_keepalive=True,
            retry_on_timeout=True,
            max_connections=20,
        )
    return _async_redis_client