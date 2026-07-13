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


_EXCHANGE_PREFIX_MAP: dict[str, str] = {
    "6": "SH",
    "0": "SZ",
    "3": "SZ",
    "4": "BJ",
    "8": "BJ",
}


def normalize_symbol(raw_code: str) -> str:
    """把纯数字代码转成带交易所后缀格式，如 600519 -> 600519.SH"""
    if "." in raw_code:
        return raw_code
    prefix = raw_code[0] if raw_code else ""
    suffix = _EXCHANGE_PREFIX_MAP.get(prefix, "SH")
    return f"{raw_code}.{suffix}"
