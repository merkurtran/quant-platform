from enum import Enum
import bisect
from decimal import Decimal 

from shared.market_data.utils import _safe_decimal

class AdjustMethod(str, Enum):
    NONE = "none"
    QFQ_RATIO = "qfq_ratio"       # 比例前复权(本期实现)
    QFQ_DIFF = "qfq_diff"          # 差值前复权(预留,对齐东财/同花顺,暂不实现)
    HFQ_RATIO = "hfq_ratio"        # 比例后复权(预留)
    HFQ_DIFF = "hfq_diff"          # 差值后复权(预留)


def _get_theoretical_price(prev_close: Decimal, action: dict) -> Decimal | None:
    """计算单个除权事件的理论除权价格(与复权方式无关)"""
    cash = _safe_decimal(action.get("cash_per_share", 0))
    stock_ratio = _safe_decimal(action.get("stock_ratio", 0))
    rights_price = _safe_decimal(action.get("rights_price", 0))
    rights_ratio = _safe_decimal(action.get("rights_ratio", 0))
    if rights_price > 0 and rights_ratio > 0:
        theoretical = (prev_close + rights_price * rights_ratio) / (1 + rights_ratio)
        return theoretical if theoretical > 0 else None

    # 分红/送股/两者组合,统一走这一个公式,不需要关心 action_type 具体是哪个标签
    theoretical = (prev_close - cash) / (1 + stock_ratio)
    return theoretical if theoretical > 0 else None


def _build_action_factors(raw_klines: list[dict], corporate_actions: list[dict]) -> list[tuple]:
    """"
    为除权事件构建因子列表  [(ex_date, factor), ...] 
    因子 = prev_close / theoretical_price
    所有复权方式共用此函数, 区别在于后续怎么使用这些因子
    """
    factors = []
    for action in corporate_actions:
        prev_close = _find_prev_close(raw_klines, action["ex_date"])
        if prev_close is None:
            continue
            
        theoretical = _get_theoretical_price(prev_close, action)
        if theoretical is None or theoretical <= 0:
            continue
            
        factor = prev_close / theoretical
        factors.append((action["ex_date"], factor))
    
    return factors


def _apply_qfq_ratio(raw_klines: list[dict], segment_factors: list[Decimal], ex_dates: list) -> list[dict]:
    """比例前复权"""
    result = []
    for kline in raw_klines:
        kline_date = kline["ts"].date()
        idx = bisect.bisect_right(ex_dates, kline_date)
        cumulative_factor = segment_factors[idx] if idx < len(segment_factors) else Decimal("1")
        
        adjusted = dict(kline)
        for field in ["open", "high", "low", "close"]:
            adjusted[field] = kline[field] / cumulative_factor
        result.append(adjusted)
    
    return result


def _apply_qfq_diff(raw_klines: list[dict], segment_factors: list[Decimal], ex_dates: list, original_klines: list[dict]) -> list[dict]:
    """
    预留: 差值前复权
    TODO: 实现
    """
    raise NotImplementedError("差值前复权暂未实现")


def _apply_hfq_ratio(raw_klines: list[dict], segment_factors: list[Decimal], ex_dates: list) -> list[dict]:
    """
    预留: 比例后复权
    TODO: 实现
    """
    raise NotImplementedError("比例后复权暂未实现")


def _apply_hfq_diff(raw_klines: list[dict], segment_factors: list[Decimal], ex_dates: list, original_klines: list[dict]) -> list[dict]:
    """
    预留: 差值后复权
    TODO: 实现
    """
    raise NotImplementedError("差值后复权暂未实现")


def calculate_adjusted_prices(raw_klines: list[dict], corporate_actions: list[dict], method: AdjustMethod) -> list[dict]:
    """根据复权方式计算复权后的价格"""
    if method == AdjustMethod.NONE:
        return raw_klines
    
    if not corporate_actions:
        return raw_klines
    
    action_factors = _build_action_factors(raw_klines, corporate_actions)
    if not action_factors:
        return raw_klines 
    
    ex_dates = [ed for ed, _ in action_factors]

    if method in (AdjustMethod.QFQ_RATIO, AdjustMethod.QFQ_DIFF):
        # 前复权: 从后往前累乘 (最新的K线不受影响)
        segment_factors = [Decimal("1")] * len(action_factors)
        cumulative = Decimal("1")
        for i in range(len(action_factors) - 1, -1, -1):
            cumulative *= action_factors[i][1]
            segment_factors[i] = cumulative
    
    elif method in (AdjustMethod.HFQ_RATIO, AdjustMethod.HFQ_DIFF):
        # 后复权: 从前往后累乘 (最老的K线不受影响)
        segment_factors = [Decimal("1")] * len(action_factors)
        cumulative = Decimal("1")
        for i in range(len(action_factors)):
            cumulative *= action_factors[i][1]
            segment_factors[i] = cumulative
    else:
        raise ValueError(f"未知复权方式: {method}")
    
    if method == AdjustMethod.QFQ_RATIO:
        return _apply_qfq_ratio(raw_klines, segment_factors, ex_dates)
    elif method == AdjustMethod.QFQ_DIFF:
        return _apply_qfq_diff(raw_klines, segment_factors, ex_dates, raw_klines)
    elif method == AdjustMethod.HFQ_RATIO:
        return _apply_hfq_ratio(raw_klines, segment_factors, ex_dates)
    elif method == AdjustMethod.HFQ_DIFF:
        return _apply_hfq_diff(raw_klines, segment_factors, ex_dates, raw_klines)


def _find_prev_close(raw_klines: list[dict], ex_date) -> Decimal | None:
    """在原始K线里找除权除息日之前最近一个交易日的收盘价"""
    candidates = [k for k in raw_klines if k["ts"].date() < ex_date]
    if not candidates:
        return None
    return candidates[-1]["close"]
