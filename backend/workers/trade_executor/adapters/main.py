import asyncio

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .consumer import run_consumer
from .outbox_processor import run_outbox_processor
from .risk_control import RiskControl
from app.core.config import get_settings


settings = get_settings()


async def main():
    redis_client = aioredis.from_url(settings.redis.url, decode_responses=True)

    engine = create_async_engine(settings.db.url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    risk_control = RiskControl(redis_client)

    # 并发启动 Consumer (Redis BLPOP) + Outbox Processor (DB 轮询)
    await asyncio.gather(
        run_consumer(redis_client, session_factory, risk_control),
        run_outbox_processor(session_factory),
    )


if __name__ == "__main__":
    asyncio.run(main())
