import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BizException, BizErrorCode
from app.models.trading import AuditLog, BrokerAccount, Order, Position, TradeOutbox
from shared.redis_client import get_async_redis_client


ORDER_QUEUE = "trade:order_queue"


async def create_order(
    session: AsyncSession,
    *,
    user_id: int,
    broker_account_id: int,
    symbol: str,
    side: str,
    order_type: str,
    price: float | None,
    volume: float,
    strategy_id: int | None = None,
) -> Order:
    stmt = select(BrokerAccount).where(
        BrokerAccount.id == broker_account_id,
        BrokerAccount.user_id == user_id,
        BrokerAccount.status == "active"
    )
    result = await session.execute(stmt)
    account = result.scalar_one_or_none()
    if account is None:
        raise BizException(BizErrorCode.NOT_FOUND, "Broker account not found or not owned by user", status_code=404)
    client_order_id = f"CL-{uuid.uuid4().hex[:16].upper()}"

    order = Order(
        user_id=user_id,
        broker_account_id=broker_account_id,
        strategy_id=strategy_id,
        client_order_id=client_order_id,
        symbol=symbol.upper(),
        side=side,
        order_type=order_type,
        price=price,
        volume=volume,
        status="pending",
        origin="manual" if strategy_id is None else "strategy",
    )

    audit = AuditLog(
        user_id=user_id,
        action="order_create",
        actor_type="manual" if strategy_id is None else "strategy",
        target_type="order",
        detail={
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "price": price,
            "volume": volume,
        },
    )
    session.add(order)
    session.add(audit)
    await session.commit()
    await session.refresh(order)
    redis_client = get_async_redis_client()
    await redis_client.rpush(
        ORDER_QUEUE,
        json.dumps(
            {
                "user_id": user_id,
                "broker_account_id": broker_account_id,
                "client_order_id": client_order_id,
            }
        ),
    )
    return order


async def cancel_order(session: AsyncSession, user_id: int, order_id: int) -> Order | None:
    stmt = (
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .with_for_update()
    )
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise BizException(BizErrorCode.NOT_FOUND, "Order not found", status_code=404)

    if order.status not in ("pending", "submitted", "partial_filled"):
        raise BizException(BizErrorCode.ORDER_CANNOT_CANCEL, "Order cannot be cancelled", status_code=400)

    outbox_result = await session.execute(
        select(TradeOutbox)
        .where(TradeOutbox.order_id == order.id, TradeOutbox.status == "pending")
        .with_for_update()
    )
    outbox = outbox_result.scalar_one_or_none()
    if outbox is not None:
        outbox.status = "skipped"
        outbox.processed_at = datetime.now(timezone.utc)
        outbox.last_error = "Cancelled by user before execution"

    if order.reserved_cash > 0:
        account_result = await session.execute(
            select(BrokerAccount)
            .where(BrokerAccount.id == order.broker_account_id)
            .with_for_update()
        )
        account = account_result.scalar_one()
        account.frozen_cash -= order.reserved_cash
        account.cash_balance += order.reserved_cash
        order.reserved_cash = 0

    if order.reserved_volume > 0:
        position_result = await session.execute(
            select(Position)
            .where(
                Position.broker_account_id == order.broker_account_id,
                Position.symbol == order.symbol,
            )
            .with_for_update()
        )
        position = position_result.scalar_one_or_none()
        if position is not None:
            position.frozen_volume -= order.reserved_volume
        order.reserved_volume = 0

    previous_status = order.status
    order.status = "cancelled"
    order.updated_at = datetime.now(timezone.utc)
    session.add(
        AuditLog(
            user_id=user_id,
            action="order_cancel",
            actor_type="manual",
            target_type="order",
            target_id=order.id,
            detail={"previous_status": previous_status},
        )
    )
    await session.commit()
    await session.refresh(order)
    return order


async def get_orders(
    session: AsyncSession,
    user_id: int,
    *,
    status: str | None = None,
    symbol: str | None = None,
    strategy_id: int | None = None,
    page: int = 1,
    page_size: int | None = None,
) -> tuple[list[Order], int]:
    from app.core.config import get_settings as _gs
    if page_size is None:
        page_size = _gs().default_page_size
    stmt = select(Order).where(Order.user_id == user_id)

    if status:
        stmt = stmt.where(Order.status == status)
    if symbol:
        stmt = stmt.where(Order.symbol == symbol)
    if strategy_id is not None:
        stmt = stmt.where(Order.strategy_id == strategy_id)

    # count
    count_stmt = select(func.count()).select_from(Order).where(Order.user_id == user_id)
    if status:
        count_stmt = count_stmt.where(Order.status == status)
    if symbol:
        count_stmt = count_stmt.where(Order.symbol == symbol)
    result = await session.execute(count_stmt)
    total = result.scalar() or 0

    stmt = stmt.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(stmt)
    orders = list(result.scalars().all())

    return orders, total


async def get_positions(
    session: AsyncSession,
    user_id: int,
) -> list[Position]:
    stmt = (
        select(Position)
        .join(BrokerAccount, BrokerAccount.id == Position.broker_account_id)
        .where(BrokerAccount.user_id == user_id)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
