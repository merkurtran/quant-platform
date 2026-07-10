from fastapi import APIRouter, Depends

from app.core.deps import get_current_user, get_async_db
from app.core.exceptions import BizException, BizErrorCode
from app.core.rate_limiter import rate_limiter
from app.schemas.trading import (
    BrokerAccountCreate,
    BrokerAccountOut,
    CreateOrderRequest,
    OrderOut,
    PositionOut,
)
from app.services import order_service

router = APIRouter(prefix="/api/v1", tags=["trading"])


@router.post("/broker_accounts", response_model=BrokerAccountOut)
async def create_broker_account(
    body: BrokerAccountCreate,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from app.models.trading import BrokerAccount

    account = BrokerAccount(
        user_id=user.id,
        broker_type=body.broker_type,
        account_alias=body.account_alias,
        status="active",
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return account


@router.get("/broker_accounts", response_model=list[BrokerAccountOut])
async def list_broker_accounts(
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.trading import BrokerAccount

    stmt = select(BrokerAccount).where(BrokerAccount.user_id == user.id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/orders", response_model=OrderOut)
async def create_order(
    body: CreateOrderRequest,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    allowed = await rate_limiter.check(f"order:user:{user.id}", limit=20)
    if not allowed:
        raise BizException(
            BizErrorCode.RATE_LIMITED,
            "Rate limit exceeded (max 20 orders per minute)",
            status_code=429,
        )

    order = await order_service.create_order(
        session=db,
        user_id=user.id,
        broker_account_id=body.broker_account_id,
        symbol=body.symbol,
        side=body.side,
        order_type=body.order_type,
        price=float(body.price) if body.price else None,
        volume=float(body.volume),
    )
    return order


@router.get("/orders", response_model=list[OrderOut])
async def list_orders(
    status: str | None = None,
    symbol: str | None = None,
    strategy_id: int | None = None,
    page: int = 1,
    page_size: int = 20,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    orders, _ = await order_service.get_orders(
        db,
        user.id,
        status=status,
        symbol=symbol,
        strategy_id=strategy_id,
        page=page,
        page_size=page_size,
    )
    return orders


@router.delete("/orders/{order_id}", response_model=OrderOut)
async def cancel_order(
    order_id: int,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    order = await order_service.cancel_order(db, user.id, order_id)
    return order


@router.get("/positions", response_model=list[PositionOut])
async def list_positions(
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    positions = await order_service.get_positions(db, user.id)
    return positions