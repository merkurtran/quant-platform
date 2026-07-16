import asyncio
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal

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
        from app.models.trading import AuditLog, BrokerAccount, Order, Position

        stmt = (
            select(BrokerAccount)
            .where(BrokerAccount.id == broker_account_id)
            .with_for_update()
        )
        result = await session.execute(stmt)
        account = result.scalar_one_or_none()

        if account is None or account.status != "active":
            await _reject_order(
                db_session_factory, user_id, client_order_id, "Account not found or inactive"
            )
            return

        # 获取订单记录（幂等检查）
        stmt = (
            select(Order)
            .where(
                Order.broker_account_id == broker_account_id,
                Order.client_order_id == client_order_id,
            )
            .with_for_update()
        )
        result = await session.execute(stmt)
        order = result.scalar_one_or_none()

        if order is None:
            logger.error(f"Order {client_order_id} not found in DB")
            return

        if order.status not in ("pending",):
            logger.warning(f"Order {client_order_id} already processed, status={order.status}")
            return

        if account.broker_type == "mock":
            estimated_price = order.price
            if estimated_price is None:
                from app.models.market import Klines

                price_result = await session.execute(
                    select(Klines.close)
                    .where(Klines.symbol == order.symbol)
                    .order_by(Klines.ts.desc())
                    .limit(1)
                )
                market_price = price_result.scalar_one_or_none()
                if market_price is not None:
                    direction = Decimal("1") if order.side == "buy" else Decimal("-1")
                    estimated_price = market_price * (
                        Decimal("1") + direction * account.slippage_rate
                    )

            rejection_reason = None
            if estimated_price is None:
                rejection_reason = "No market price available"
            elif order.side == "buy":
                gross = estimated_price * order.volume
                commission = max(
                    gross * account.commission_rate,
                    account.minimum_commission,
                ).quantize(Decimal("0.01"))
                reserve = (gross + commission).quantize(Decimal("0.01"))
                if account.cash_balance < reserve:
                    rejection_reason = "Insufficient cash"
                else:
                    account.cash_balance -= reserve
                    account.frozen_cash += reserve
                    order.reserved_cash = reserve
            else:
                pos_result = await session.execute(
                    select(Position)
                    .where(
                        Position.broker_account_id == broker_account_id,
                        Position.symbol == order.symbol,
                    )
                    .with_for_update()
                )
                position = pos_result.scalar_one_or_none()
                available_volume = (
                    position.volume - position.frozen_volume
                    if position is not None
                    else Decimal("0")
                )
                if available_volume < order.volume:
                    rejection_reason = "Insufficient position"
                else:
                    position.frozen_volume += order.volume
                    order.reserved_volume = order.volume

            if rejection_reason is not None:
                order.status = "rejected"
                order.reject_reason = rejection_reason
                order.updated_at = datetime.now(timezone.utc)
                session.add(
                    AuditLog(
                        user_id=user_id,
                        action="order_rejected",
                        actor_type="system",
                        target_type="order",
                        target_id=order.id,
                        detail={"reason": rejection_reason},
                    )
                )
                await session.commit()
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
            order.reject_reason = reason
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
