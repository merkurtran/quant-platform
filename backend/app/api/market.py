from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

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
    create_watchlist,
)
from shared.db.session import get_db


router = APIRouter(prefix="/api/v1/market", tags=["market"])

@router.get("/klines", response_model=KlineListResponse)
def list_klines(
    symbol: str,
    period: str = "1d",
    limit: int = 300,
    db: Session = Depends(get_db)
):
    klines = get_klines(db, symbol=symbol, period=period, limit=limit)
    return KlineListResponse(
        symbol=symbol,
        period=period,
        items=[KlineItem.model_validate(k) for k in klines],
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Watchlist not found")
    return {"code": 0, "message": "deleted"}


@router.post("/watchlists", response_model=WatchlistPublic)
def create_watchlist_endpoint(
    payload: CreateWatchlistRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    watchlist = create_watchlist(db, user_id=current_user.id, name=payload.name)
    return WatchlistPublic.model_validate(watchlist)