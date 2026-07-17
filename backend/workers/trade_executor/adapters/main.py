import asyncio
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from shared.db.session import AsyncSessionLocal
from shared.redis_client import get_async_redis_client
import app.models.strategy  # noqa: F401 - register FK targets for worker sessions
import app.models.user  # noqa: F401 - register FK targets for worker sessions
from workers.trade_executor.adapters.consumer import run_consumer
from workers.trade_executor.adapters.outbox_processor import run_outbox_processor
from workers.trade_executor.adapters.risk_control import RiskControl


async def main():
    redis_client = get_async_redis_client()

    risk_control = RiskControl(redis_client)

    # 并发启动 Consumer (Redis BLPOP) + Outbox Processor (DB 轮询)
    await asyncio.gather(
        run_consumer(redis_client, AsyncSessionLocal, risk_control),
        run_outbox_processor(AsyncSessionLocal),
    )


if __name__ == "__main__":
    asyncio.run(main())
