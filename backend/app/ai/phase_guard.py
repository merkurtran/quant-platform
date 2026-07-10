from datetime import datetime, time
from enum import Enum

# A股交易时段
_A_MORNING_START = time(9, 30)
_A_MORNING_END = time(11, 30)
_A_AFTERNOON_START = time(13, 0)
_A_AFTERNOON_END = time(15, 0)

# 集合竞价阶段
_A_CALL_AUCTION_START = time(9, 15)
_A_CALL_AUCTION_END = time(9, 25)


class MarketPhase(str, Enum):
    PRE_CALL = "pre_call"          # 9:15 前
    CALL_AUCTION = "call_auction"  # 9:15–9:25
    PRE_OPEN = "pre_open"          # 9:25–9:30
    MORNING = "morning"            # 9:30–11:30
    LUNCH = "lunch"                # 11:30–13:00
    AFTERNOON = "afternoon"        # 13:00–15:00
    POST_MARKET = "post_market"    # 15:00 后
    NON_TRADING = "non_trading"    # 非交易日


def get_market_phase(now: datetime | None = None) -> MarketPhase:
    """识别当前市场阶段。非交易日检查需要外部传入 is_trading_day。"""
    if now is None:
        now = datetime.now()

    t = now.time()
    if now.weekday() >= 5:
        return MarketPhase.NON_TRADING

    if t < _A_CALL_AUCTION_START:
        return MarketPhase.PRE_CALL
    if t < _A_CALL_AUCTION_END:
        return MarketPhase.CALL_AUCTION
    if t < _A_MORNING_START:
        return MarketPhase.PRE_OPEN
    if t < _A_MORNING_END:
        return MarketPhase.MORNING
    if t < _A_AFTERNOON_START:
        return MarketPhase.LUNCH
    if t < _A_AFTERNOON_END:
        return MarketPhase.AFTERNOON
    return MarketPhase.POST_MARKET


# 各阶段对 AI 行为的约束
PHASE_GUARD_PROMPTS = {
    MarketPhase.NON_TRADING: (
        "当前是非交易日。分析应基于最近一个交易日的收盘数据。"
        "不得伪造盘中走势或实时价格变动。"
    ),
    MarketPhase.PRE_CALL: (
        "当前是盘前阶段，市场尚未开盘。分析只能基于前一交易日收盘数据做开盘计划，"
        "不得描述已发生的盘中走势。所有价格判断必须标注'基于昨日收盘价'。"
    ),
    MarketPhase.CALL_AUCTION: (
        "当前是集合竞价阶段。价格波动不代表实盘成交方向，分析中需降低此阶段信号的置信度。"
    ),
    MarketPhase.PRE_OPEN: (
        "距离开盘不足5分钟。可提及集合竞价结果，但禁止声称盘中走势。"
    ),
    MarketPhase.LUNCH: (
        "当前是午间休市。分析基于上午收盘数据，下午走势存在不确定性。"
    ),
    MarketPhase.POST_MARKET: (
        "当前已收盘。分析基于完整交易日数据，可做次日预判。"
    ),
}
