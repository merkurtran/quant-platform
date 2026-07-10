"""基于 Redis 的滑动窗口限流器，支持多进程/多实例部署。"""
import time
import uuid
from shared.redis_client import get_async_redis_client

_RATE_LIMIT_SCRIPT = """
local key   = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local now   = tonumber(ARGV[3])

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)
if count >= limit then
    return 0
end
redis.call('ZADD', key, now, ARGV[4])
redis.call('EXPIRE', key, window + 1)
return 1
"""


class RateLimiter:
    """滑动窗口限流器。Sorted Set 存储时间戳，Lua 脚本保证 check-and-add 原子性。"""

    async def check(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = time.time()
        member = f"{now}:{uuid.uuid4().hex[:8]}"
        result = await (await get_async_redis_client()).eval(
            _RATE_LIMIT_SCRIPT, 1, key, limit, window_seconds, now, member
        )
        return bool(result)


rate_limiter = RateLimiter()
