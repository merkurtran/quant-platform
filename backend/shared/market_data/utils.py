import logging
import pandas as pd
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


def _safe_decimal(value) -> Decimal:
    """
    把可能是 NaN/None 的数值安全转成 Decimal。

    - None / NaN → Decimal("0") 并记录 WARNING
    - 正常数值 → Decimal(str(value))
    - 无法转换的异常值 → Decimal("0") 并记录 ERROR
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        logger.warning(f"转换 NaN/None 为 Decimal(0): raw={value!r}, type={type(value).__name__}")
        return Decimal("0")

    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f"无法转换为 Decimal: raw={value!r}, error={e}")
        return Decimal("0")
