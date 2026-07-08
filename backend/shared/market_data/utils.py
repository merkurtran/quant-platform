import pandas as pd
from decimal import Decimal 


def _safe_decimal(value) -> Decimal:
    """把可能是 NaN/None 的数值,安全转成 Decimal,NaN 统一当0处理"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return Decimal("0")
    return Decimal(str(value))
