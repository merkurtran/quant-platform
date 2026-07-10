from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BrokerAccountCreate(BaseModel):
    broker_type: str = Field(default="mock", max_length=32)
    account_alias: str = Field(max_length=64)


class BrokerAccountOut(BaseModel):
    id: int
    broker_type: str
    account_alias: str
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateOrderRequest(BaseModel):
    broker_account_id: int
    symbol: str = Field(min_length=1, max_length=16)
    side: str = Field(pattern="^(buy|sell)$")
    order_type: str = Field(default="limit", pattern="^(limit|market)$")
    price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=3)
    volume: Decimal = Field(gt=0, max_digits=18, decimal_places=2)


class OrderOut(BaseModel):
    id: int
    user_id: int
    broker_account_id: int
    strategy_id: Optional[int] = None
    client_order_id: str
    symbol: str
    side: str
    order_type: str
    price: Optional[Decimal] = None
    volume: Decimal
    filled_volume: Decimal
    status: str
    broker_order_id: Optional[str] = None
    origin: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PositionOut(BaseModel):
    broker_account_id: int
    symbol: str
    volume: Decimal
    avg_cost: Decimal
    updated_at: datetime

    model_config = {"from_attributes": True}
