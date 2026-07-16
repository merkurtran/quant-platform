import base64
import time
from datetime import date
from decimal import Decimal, InvalidOperation

import httpx
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from shared.market_data.base import MarketDataProvider
from shared.market_data.exceptions import DataFormatError, DataSourceConnectionError


class CninfoProvider(MarketDataProvider):
    """Corporate actions from CNINFO; price adjustment remains local."""

    _URL = "https://webapi.cninfo.com.cn/api/sysapi/p_sysapi1139"
    _AES_KEY = b"1234567887654321"

    def __init__(self) -> None:
        self._client = httpx.Client(timeout=20, trust_env=False)

    @classmethod
    def _make_enckey(cls) -> str:
        padder = padding.PKCS7(128).padder()
        payload = padder.update(str(int(time.time())).encode()) + padder.finalize()
        encryptor = Cipher(
            algorithms.AES(cls._AES_KEY),
            modes.CBC(cls._AES_KEY),
        ).encryptor()
        encrypted = encryptor.update(payload) + encryptor.finalize()
        return base64.b64encode(encrypted).decode()

    @staticmethod
    def _decimal(value: object) -> Decimal:
        if value is None:
            return Decimal("0")
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return Decimal("0")

    def get_corporate_actions(
        self,
        symbol: str,
        start_date: date | None = None,
    ) -> list[dict]:
        headers = {
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Enckey": self._make_enckey(),
            "Origin": "https://webapi.cninfo.com.cn",
            "Referer": "https://webapi.cninfo.com.cn/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
            "X-Requested-With": "XMLHttpRequest",
        }
        try:
            response = self._client.post(
                self._URL,
                params={"scode": symbol.split(".")[0]},
                headers=headers,
            )
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise DataSourceConnectionError(
                f"CNINFO corporate actions failed for {symbol}: {exc}"
            ) from exc

        records = body.get("records")
        if not isinstance(records, list):
            raise DataFormatError(f"CNINFO returned invalid records for {symbol}")

        actions: list[dict] = []
        for record in records:
            try:
                ex_date = date.fromisoformat(record["F020D"])
            except (KeyError, TypeError, ValueError):
                continue
            if start_date is not None and ex_date < start_date:
                continue

            stock_ratio = (
                self._decimal(record.get("F010N"))
                + self._decimal(record.get("F011N"))
            ) / Decimal("10")
            cash_per_share = self._decimal(record.get("F012N")) / Decimal("10")
            if stock_ratio == 0 and cash_per_share == 0:
                continue
            actions.append(
                {
                    "ex_date": ex_date,
                    "action_type": "stock_split" if stock_ratio > 0 else "dividend",
                    "cash_per_share": cash_per_share,
                    "stock_ratio": stock_ratio,
                    "rights_price": Decimal("0"),
                    "rights_ratio": Decimal("0"),
                }
            )
        return sorted(actions, key=lambda item: item["ex_date"])

    def get_daily_kline(self, symbol: str, start_date: str) -> list[dict]:
        raise NotImplementedError

    def get_minute_kline(
        self,
        symbol: str,
        period: str,
        start_date: str = "",
    ) -> list[dict]:
        raise NotImplementedError

    def get_all_symbols(self) -> list[str]:
        raise NotImplementedError
