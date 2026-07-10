import redis.asyncio as aioredis


class RiskControl:
    """风控门禁：基于 Redis 的全局/用户级开关。关闭时所有订单直接 reject。"""

    GLOBAL_KEY = "risk:trading_enabled:global"
    USER_KEY_PREFIX = "risk:trading_enabled:user:"

    def __init__(self, redis_client: aioredis.Redis):
        self._redis = redis_client

    async def is_trading_enabled(self, user_id: int) -> bool:
        global_enabled = await self._redis.get(self.GLOBAL_KEY)
        if global_enabled == "0":
            return False
        user_enabled = await self._redis.get(f"{self.USER_KEY_PREFIX}{user_id}")
        if user_enabled == "0":
            return False
        return True

    async def set_global_enabled(self, enabled: bool) -> None:
        await self._redis.set(self.GLOBAL_KEY, "1" if enabled else "0")

    async def set_user_enabled(self, user_id: int, enabled: bool) -> None:
        await self._redis.set(
            f"{self.USER_KEY_PREFIX}{user_id}", "1" if enabled else "0"
        )
