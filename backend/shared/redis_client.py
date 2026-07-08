import redis
import redis.asyncio as redis_asyncio

from app.core.config import get_settings


_redis_client: redis.Redis | None = None
_async_redis_client: redis_asyncio.Redis | None = None


def get_redis_client() -> redis.Redis:
    """同步 Redis 客户端,懒加载,首次调用时连接"""
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
    """异步 Redis 客户端,懒加载,首次调用时连接"""
    global _async_redis_client
    if _async_redis_client is None:
        settings = get_settings()
        _async_redis_client = redis_asyncio.from_url(
            settings.redis.url,
            decode_responses=True,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _async_redis_client


def __getattr__(name: str):
    """模块级懒加载代理：首次 import 该属性时才连接 Redis"""
    if name == "redis_client":
        return get_redis_client()
    if name == "async_redis_client":
        return get_async_redis_client()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")