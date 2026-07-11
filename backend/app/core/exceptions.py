from enum import IntEnum
from typing import Any


class BizErrorCode(IntEnum):
    # 通用
    UNKNOWN = 10000
    NOT_IMPLEMENTED = 10004

    # 认证/授权 10xxx
    UNAUTHORIZED = 10001
    TOKEN_EXPIRED = 10002
    FORBIDDEN = 10003

    # 资源 20xxx
    NOT_FOUND = 20001
    ALREADY_EXISTS = 20002
    CONFLICT = 20003
    ORDER_CANNOT_CANCEL = 20004

    # 参数 30xxx
    VALIDATION_ERROR = 30001

    # 业务 40xxx
    RATE_LIMITED = 40001
    TRADE_FAILED = 40002
    LLM_ERROR = 40003
    BACKTEST_FAILED = 40004


class BizException(Exception):
    def __init__(
        self,
        code: BizErrorCode,
        message: str = "",
        data: Any = None,
        status_code: int = 400,
        headers: dict[str, str] | None = None,
    ):
        self.code = code
        self.message = message
        self.data = data
        self.status_code = status_code
        self.headers = headers
