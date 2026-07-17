from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, model_validator


class BrokerAccountCreate(BaseModel):
    broker_type: str = Field(default="mock", max_length=32)
    account_alias: str = Field(max_length=64)
    initial_cash: Decimal = Field(default=Decimal("1000000"), gt=0, max_digits=18, decimal_places=2)


class BrokerAccountOut(BaseModel):
    id: int
    broker_type: str
    account_alias: str
    status: str
    initial_cash: Decimal
    cash_balance: Decimal
    frozen_cash: Decimal
    commission_rate: Decimal
    minimum_commission: Decimal
    stamp_duty_rate: Decimal
    slippage_rate: Decimal
    created_at: datetime

    model_config = {"from_attributes": True}


class CreateOrderRequest(BaseModel):
    broker_account_id: int
    symbol: str = Field(min_length=1, max_length=16)
    side: str = Field(pattern="^(buy|sell)$")
    order_type: str = Field(default="limit", pattern="^(limit|market)$")
    price: Optional[Decimal] = Field(default=None, max_digits=12, decimal_places=3)
    volume: Decimal = Field(gt=0, max_digits=18, decimal_places=2)

    @model_validator(mode="after")
    def validate_order(self):
        if self.order_type == "limit" and self.price is None:
            raise ValueError("Limit orders require a price")
        if self.volume != self.volume.to_integral_value():
            raise ValueError("A-share order volume must be an integer")
        if self.volume % 100 != 0:
            raise ValueError("A-share order volume must be a multiple of 100")
        return self


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
    filled_price: Optional[Decimal] = None
    commission: Decimal
    stamp_duty: Decimal
    reject_reason: Optional[str] = None
    reserved_cash: Decimal
    reserved_volume: Decimal
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
    available_volume: Decimal
    pending_settlement_volume: Decimal
    frozen_volume: Decimal
    last_buy_trade_date: Optional[date] = None
    updated_at: datetime

    model_config = {"from_attributes": True}
