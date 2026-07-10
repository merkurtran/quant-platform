import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import BizException, BizErrorCode
from app.models.trading import AuditLog, BrokerAccount, Order, Position


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
        symbol=symbol,
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
    return order


async def cancel_order(session: AsyncSession, user_id: int, order_id: int) -> Order | None:
    stmt = select(Order).where(Order.id == order_id, Order.user_id == user_id)
    result = await session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise BizException(BizErrorCode.NOT_FOUND, "Order not found", status_code=404)

    if order.status not in ("pending", "submitted", "partial_filled"):
        raise BizException(BizErrorCode.ORDER_CANNOT_CANCEL, "Order cannot be cancelled", status_code=400)

    order.status = "cancelled"
    order.updated_at = datetime.now(timezone.utc)
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
    broker_account_id: int,
) -> list[Position]:
    stmt = select(Position).where(Position.broker_account_id == broker_account_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())
