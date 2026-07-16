import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError

from app.schemas.trading import CreateOrderRequest
from app.services.order_service import cancel_order, create_order
from workers.trade_executor.adapters.base import OrderRequest
from workers.trade_executor.adapters.mock_adapter import MockAdapter


@pytest.mark.asyncio
async def test_create_order_enqueues_for_trade_executor():
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = MagicMock(id=7)
    session.execute.return_value = result
    session.add = MagicMock()
    redis = AsyncMock()

    with patch(
        "app.services.order_service.get_async_redis_client",
        return_value=redis,
    ):
        order = await create_order(
            session,
            user_id=1,
            broker_account_id=7,
            symbol="000001.SZ",
            side="buy",
            order_type="limit",
            price=10,
            volume=100,
        )

    payload = json.loads(redis.rpush.await_args.args[1])
    assert redis.rpush.await_args.args[0] == "trade:order_queue"
    assert payload == {
        "user_id": 1,
        "broker_account_id": 7,
        "client_order_id": order.client_order_id,
    }


def test_mock_adapter_is_instantiable_and_reports_filled_volume():
    adapter = MockAdapter(MagicMock(), broker_account_id=7)

    result = adapter.place_order(
        OrderRequest(
            symbol="000001.SZ",
            side="buy",
            order_type="limit",
            price=Decimal("10"),
            volume=Decimal("100"),
        )
    )

    assert result.status == "filled"
    assert result.filled_volume == Decimal("100")
    assert adapter.get_orders() == [
        {"broker_order_id": result.broker_order_id, "status": "filled"}
    ]
    assert adapter.cancel_order(result.broker_order_id) is False


def test_a_share_order_requires_limit_price_and_board_lot():
    with pytest.raises(ValidationError):
        CreateOrderRequest(
            broker_account_id=7,
            symbol="000001.SZ",
            side="buy",
            order_type="limit",
            volume=Decimal("100"),
        )

    with pytest.raises(ValidationError):
        CreateOrderRequest(
            broker_account_id=7,
            symbol="000001.SZ",
            side="buy",
            order_type="market",
            volume=Decimal("150"),
        )


@pytest.mark.asyncio
async def test_cancel_submitted_order_skips_pending_outbox():
    session = AsyncMock()
    session.add = MagicMock()
    order = MagicMock(
        id=12,
        status="submitted",
        reserved_cash=Decimal("0"),
        reserved_volume=Decimal("0"),
    )
    outbox = MagicMock(status="pending", processed_at=None, last_error=None)
    order_result = MagicMock()
    order_result.scalar_one_or_none.return_value = order
    outbox_result = MagicMock()
    outbox_result.scalar_one_or_none.return_value = outbox
    session.execute.side_effect = [order_result, outbox_result]

    cancelled = await cancel_order(session, user_id=1, order_id=12)

    assert cancelled is order
    assert order.status == "cancelled"
    assert outbox.status == "skipped"
    assert outbox.last_error == "Cancelled by user before execution"
    session.commit.assert_awaited_once()
