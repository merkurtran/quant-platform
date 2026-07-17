import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .base import BrokerAdapter, OrderRequest, OrderResult


class MockAdapter(BrokerAdapter):
    """模拟盘实现：内存记账 + 数据库落盘。place_order 同步立即成交。"""

    def __init__(self, db_session_factory: async_sessionmaker[AsyncSession], broker_account_id: int):
        self._db_factory = db_session_factory
        self._account_id = broker_account_id
        self._cash = Decimal("1000000")
        self._initial_cash = self._cash  # 用于计算收益率
        self._positions: dict[str, dict] = {}  # {symbol: {volume, avg_cost}}
        self._orders: dict[str, dict] = {}

    def connect(self, credentials: dict) -> bool:
        return True

    def disconnect(self) -> None:
        pass

    def get_balance(self) -> dict:
        market_value = Decimal("0")
        for p in self._positions.values():
            market_value += p["volume"] * p["avg_cost"]
        return {
            "cash": float(self._cash),
            "market_value": float(market_value),
            "total_asset": float(self._cash + market_value),
        }

    def get_positions(self) -> list[dict]:
        return [
            {"symbol": s, "volume": float(p["volume"]), "avg_cost": float(p["avg_cost"])}
            for s, p in self._positions.items()
        ]

    def place_order(self, request: OrderRequest) -> OrderResult:
        broker_order_id = f"MOCK-{uuid.uuid4().hex[:12].upper()}"
        self._orders[broker_order_id] = {"status": "filled"}
        return OrderResult(
            broker_order_id=broker_order_id,
            status="filled",
            filled_volume=request.volume,
        )

    def cancel_order(self, broker_order_id: str) -> bool:
        order = self._orders.get(broker_order_id)
        if order is None or order["status"] == "filled":
            return False
        order["status"] = "cancelled"
        return True

    def get_orders(self) -> list[dict]:
        return [
            {"broker_order_id": broker_order_id, **order}
            for broker_order_id, order in self._orders.items()
        ]
