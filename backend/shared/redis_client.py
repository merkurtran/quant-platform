import redis
import redis.asyncio as redis_asyncio

from app.core.config import get_settings


settings = get_settings()

# 同步客户端: 给 worker 进程(market_worker/strategy_worker/trade_executor)用
redis_client: redis.Redis = redis.Redis.from_url(settings.redis.url, decode_responses=True)

# 异步客户端: 给 FastAPI 的 WebSocket 推送这些异步场景用
async_redis_client: redis_asyncio.Redis = redis_asyncio.from_url(settings.redis.url, decode_responses=True)