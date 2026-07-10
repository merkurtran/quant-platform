from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from enum import Enum

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.market import (
    KlineListResponse,
    KlineItem,
    WatchlistPublic,
    AddWatchlistItemRequest,
    WatchlistItemPublic,
    CreateWatchlistRequest,
)
from app.services.market_service import (
    get_klines,
    get_watchlists,
    add_watchlist_item,
    remove_watchlist_item,
    WatchlistNotFoundError,
    WatchlistItemAlreadyExistsError,
    WatchlistItemNotFoundError,
    create_watchlist,
    get_klines_with_adjustment
)
from shared.db.session import get_db
from shared.market_data.adjustment import AdjustMethod


class PublicAdjustParam(str, Enum):
    """API 公开的复权参数，取值与产品文档保持一致"""
    NONE = "none"
    QFQ = "qfq"

# 公开参数到内部 AdjustMethod 的映射
_PUBLIC_TO_INTERNAL: dict[PublicAdjustParam, AdjustMethod] = {
    PublicAdjustParam.NONE: AdjustMethod.NONE,
    PublicAdjustParam.QFQ: AdjustMethod.QFQ_RATIO,
}

router = APIRouter(prefix="/api/v1/market", tags=["market"])

VALID_PERIODS = frozenset({"1m", "5m", "15m", "30m", "60m", "1d", "1w", "1M"})

@router.get("/klines", response_model=KlineListResponse)
def list_klines(
    symbol: str = Query(..., min_length=1),
    period: str = Query("1d", pattern=r"^(1m|5m|15m|30m|60m|1d|1w|1M)$"),
    limit: int = Query(300, ge=1, le=2000),
    adjust: PublicAdjustParam = PublicAdjustParam.QFQ,
    start: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    end: str | None = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    internal_method = _PUBLIC_TO_INTERNAL[adjust]
    try:
        items = get_klines_with_adjustment(db, symbol, period, limit, internal_method, start=start, end=end)
    except NotImplementedError as e:
        raise BizException(BizErrorCode.NOT_IMPLEMENTED, str(e), status_code=501)
    return KlineListResponse(
        symbol=symbol,
        period=period,
        adjust=adjust.value,
        items=[KlineItem.model_validate(item) for item in items],
    )


@router.get("/watchlists", response_model=list[WatchlistPublic])
def list_watchlists(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    watchlists = get_watchlists(db, user_id=current_user.id)
    return [WatchlistPublic.model_validate(w) for w in watchlists]


@router.post("/watchlists/{watchlist_id}/items", response_model=WatchlistItemPublic)
def add_item(
    watchlist_id: int,
    payload: AddWatchlistItemRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        item = add_watchlist_item(db, watchlist_id=watchlist_id, symbol=payload.symbol, name=payload.name, user_id=current_user.id)
    except WatchlistNotFoundError:
        raise BizException(BizErrorCode.NOT_FOUND, "Watchlist not found", status_code=404)
    except WatchlistItemAlreadyExistsError:
        raise BizException(BizErrorCode.ALREADY_EXISTS, "Symbol already exists in this watchlist", status_code=409)
    return WatchlistItemPublic.model_validate(item)


@router.delete("/watchlists/{watchlist_id}/items/{symbol}")
def remove_item(
    watchlist_id: int,
    symbol: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        remove_watchlist_item(db, watchlist_id, symbol, user_id=current_user.id)
    except WatchlistNotFoundError:
        raise BizException(BizErrorCode.NOT_FOUND, "Watchlist not found", status_code=404)
    return {"code": 0, "message": "deleted"}


@router.post("/watchlists", response_model=WatchlistPublic)
def create_watchlist_endpoint(
    payload: CreateWatchlistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        watchlist = create_watchlist(db, user_id=current_user.id, name=payload.name)
    except WatchlistItemAlreadyExistsError:
        raise BizException(BizErrorCode.ALREADY_EXISTS, "Watchlist with this name already exists", status_code=409)
    return WatchlistPublic.model_validate(watchlist)