from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional


@dataclass
class OrderRequest:
    symbol: str
    side: str
    order_type: str
    price: Optional[Decimal] = None
    volume: Decimal = Decimal("0")


@dataclass
class OrderResult:
    broker_order_id: str
    status: str
    message: Optional[str] = None
    filled_volume: Optional[Decimal] = None  # 实际成交数量,None 表示未成交/未知


class BrokerAdapter(ABC):
    """所有券商接入必须实现此接口。上层业务代码只依赖此抽象类，不碰具体 SDK。"""

    @abstractmethod
    def connect(self, credentials: dict) -> bool:
        ...

    @abstractmethod
    def disconnect(self) -> None:
        ...

    @abstractmethod
    def get_balance(self) -> dict:
        ...

    @abstractmethod
    def get_positions(self) -> list[dict]:
        ...

    @abstractmethod
    def place_order(self, request: OrderRequest) -> OrderResult:
        ...

    @abstractmethod
    def cancel_order(self, broker_order_id: str) -> bool:
        ...

    @abstractmethod
    def get_orders(self) -> list[dict]:
        ...
