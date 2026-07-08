from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class KlineItem(BaseModel):
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal
    amount: Decimal | None


class KlineListResponse(BaseModel):
    symbol: str
    period: str
    adjust: str = "qfq"
    items: list[KlineItem]


class WatchlistItemPublic(BaseModel):
    symbol: str
    name: str | None
    sort_order: int
    added_at: datetime
    model_config = {"from_attributes": True}


class WatchlistPublic(BaseModel):
    id: int
    name: str
    items: list[WatchlistItemPublic]
    model_config = {"from_attributes": True}


class AddWatchlistItemRequest(BaseModel):
    symbol: str
    name: str | None = None


class CreateWatchlistRequest(BaseModel):
    name: str