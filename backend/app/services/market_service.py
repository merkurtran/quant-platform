from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.market import Klines, Watchlists, WatchlistItems, CorporateActions
from shared.market_data.adjustment import AdjustMethod, calculate_adjusted_prices


class WatchlistNotFoundError(Exception):
    pass


def _check_watchlist_ownership(db: Session, watchlist_id: int, user_id: int) -> None:
    """内部辅助函数,校验这个watchlist确实属于这个user,不属于就抛异常"""
    exists = db.query(Watchlists).filter(
        Watchlists.id == watchlist_id,
        Watchlists.user_id == user_id,
    ).first()
    if not exists:
        raise WatchlistNotFoundError(f"Watchlist {watchlist_id} not found for user {user_id}")
    

def get_klines(db: Session, symbol: str, period: str, limit: int = 300) -> list[Klines]:
    return (
        db.query(Klines)
        .filter(Klines.symbol == symbol, Klines.period == period)
        .order_by(Klines.ts.asc())
        .limit(limit)
        .all()
    )


def get_klines_with_adjustment(db: Session, symbol: str, period: str, limit: int, adjust: AdjustMethod) -> list[dict]:
    """查询 k 线并复权"""
    klines = get_klines(db, symbol, period, limit)
    raw_dicts = [
        {
            "ts": k.ts,
            "open": k.open,
            "high": k.high,
            "low": k.low,
            "close": k.close,
            "volume": k.volume,
            "amount": k.amount,
        }
        for k in klines
    ]
    if adjust == AdjustMethod.NONE:
        return raw_dicts
    
    actions = get_corporate_actions_from(db, symbol)
    return calculate_adjusted_prices(raw_dicts, actions, adjust)


def get_watchlists(db: Session, user_id: int) -> list[Watchlists]:
    return db.query(Watchlists).filter(Watchlists.user_id == user_id).all()


def add_watchlist_item(db: Session, watchlist_id: int, symbol: str, name: str | None, user_id: int) -> WatchlistItems:
    _check_watchlist_ownership(db, watchlist_id, user_id)

    item = WatchlistItems(watchlist_id=watchlist_id, symbol=symbol, name=name)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_watchlist_item(db: Session, watchlist_id: int, symbol: str, user_id: int) -> None:
    _check_watchlist_ownership(db, watchlist_id, user_id)

    db.query(WatchlistItems).filter(
        WatchlistItems.watchlist_id == watchlist_id,
        WatchlistItems.symbol == symbol,
    ).delete()
    db.commit()


def get_all_watched_symbols(db: Session) -> list[str]:
    """
    查询全平台所有用户自选股的去重股票代码列表(带交易所后缀格式,如 600519.SH)
    market_worker 定时任务用这个决定要同步哪些股票的分钟线,
    不区分具体是哪个用户关注的,只要有人关注就同步
    """
    rows = db.query(WatchlistItems.symbol).distinct().all()
    return [row[0] for row in rows]


def create_watchlist(db: Session, user_id: int, name: str) -> Watchlists:
    watchlist = Watchlists(user_id=user_id, name=name)
    db.add(watchlist)
    db.commit()
    db.refresh(watchlist)
    return watchlist


def save_corporate_actions(db: Session, symbol: str, actions: list[dict]) -> None:
    """批量 upsert 除权除息记录"""
    if not actions:
        return
    rows = [{"symbol": symbol, **action} for action in actions]
    stmt = pg_insert(CorporateActions).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["symbol", "ex_date", "action_type"],
        set_={
            "cash_per_share": stmt.excluded.cash_per_share,
            "stock_ratio": stmt.excluded.stock_ratio,
            "rights_price": stmt.excluded.rights_price,
            "rights_ratio": stmt.excluded.rights_ratio,
        },
    )
    db.execute(stmt)
    db.commit()


def get_corporate_actions_from(db: Session, symbol: str) -> list[dict]:
    """从数据库查询这支股票的除权除息记录，按 ex_date 正序， 给复权计算使用"""
    rows = (
        db.query(CorporateActions)
        .filter(CorporateActions.symbol == symbol)
        .order_by(CorporateActions.ex_date.asc())
        .all()
    )
    return [
        {
            "ex_date": r.ex_date,
            "action_type": r.action_type,
            "cash_per_share": r.cash_per_share,
            "stock_ratio": r.stock_ratio,
            "rights_price": r.rights_price,
            "rights_ratio": r.rights_ratio,
        }
        for r in rows
    ]


