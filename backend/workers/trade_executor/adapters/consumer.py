import asyncio
import json
import logging
from datetime import datetime, timezone

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .risk_control import RiskControl

logger = logging.getLogger(__name__)

# Redis 队列名
ORDER_QUEUE = "trade:order_queue"
DEAD_LETTER_QUEUE = "trade:order_dlq"
MAX_RETRIES = 3


async def run_consumer(
    redis_client: aioredis.Redis,
    db_session_factory: async_sessionmaker[AsyncSession],
    risk_control: RiskControl,
) -> None:
    """常驻循环：BLPOP 阻塞等待订单，逐一处理。失败时重试，超过上限进入死信队列。"""
    while True:
        try:
            result = await redis_client.blpop(ORDER_QUEUE, timeout=5)
            if result is None:
                continue

            _, message = result
            payload = json.loads(message)
            retry_count = payload.get("retry_count", 0)

            try:
                await _process_order(payload, db_session_factory, risk_control)
            except Exception:
                logger.exception(f"Order processing failed: {payload.get('client_order_id')}")
                if retry_count < MAX_RETRIES:
                    payload["retry_count"] = retry_count + 1
                    await redis_client.rpush(ORDER_QUEUE, json.dumps(payload))
                    await asyncio.sleep(2 ** retry_count)
                else:
                    await redis_client.rpush(DEAD_LETTER_QUEUE, message)
                    logger.error(f"Order {payload.get('client_order_id')} sent to DLQ after {MAX_RETRIES} retries")

        except Exception:
            logger.exception("Consumer loop error, will retry")
            await asyncio.sleep(1)


async def _process_order(
    payload: dict,
    db_session_factory: async_sessionmaker[AsyncSession],
    risk_control: RiskControl,
) -> None:
    user_id = payload["user_id"]
    broker_account_id = payload["broker_account_id"]
    client_order_id = payload["client_order_id"]

    # 风控检查
    if not await risk_control.is_trading_enabled(user_id):
        await _reject_order(db_session_factory, user_id, client_order_id, "Trading disabled by risk control")
        return

    async with db_session_factory() as session:
        # 获取 broker_account
        from app.models.trading import BrokerAccount, Order

        stmt = select(BrokerAccount).where(BrokerAccount.id == broker_account_id)
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None or account.status != "active":
            await _reject_order(
                db_session_factory, user_id, client_order_id, "Account not found or inactive"
            )
            return

        # 获取订单记录（幂等检查）
        stmt = select(Order).where(
            Order.broker_account_id == broker_account_id,
            Order.client_order_id == client_order_id,
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            logger.error(f"Order {client_order_id} not found in DB")
            return

        if order.status not in ("pending",):
            logger.warning(f"Order {client_order_id} already processed, status={order.status}")
            return

        # ── Outbox Pattern: 原子写入 order(submitted) + TradeOutbox ──
        # 不再直接调用券商 API，仅持久化到本地 DB；实际下单由 outbox_processor 异步完成
        now = datetime.now(timezone.utc)
        order.status = "submitted"
        order.updated_at = now

        from app.models.trading import TradeOutbox

        outbox = TradeOutbox(
            order_id=order.id,
            adapter_name=account.broker_type,
            request_json={
                "symbol": order.symbol,
                "side": order.side,
                "order_type": order.order_type,
                "price": float(order.price) if order.price else None,
                "volume": float(order.volume),
            },
            status="pending",
        )
        try:
            session.add(outbox)
            await session.commit()
        except IntegrityError:
            await session.rollback()

        logger.info(f"Order {client_order_id} → submitted, outbox id={outbox.id}")


async def _reject_order(
    db_session_factory: async_sessionmaker[AsyncSession],
    user_id: int,
    client_order_id: str,
    reason: str,
) -> None:
    async with db_session_factory() as session:
        from app.models.trading import Order, AuditLog

        stmt = select(Order).where(Order.client_order_id == client_order_id)
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if order and order.status == "pending":
            order.status = "rejected"
            order.updated_at = datetime.now(timezone.utc)

            audit = AuditLog(
                user_id=user_id,
                action="order_rejected",
                actor_type="system",
                target_type="order",
                target_id=order.id,
                detail={"reason": reason},
            )
            session.add(audit)
            await session.commit()
