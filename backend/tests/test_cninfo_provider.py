from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from shared.market_data.cninfo_provider import CninfoProvider


def test_corporate_actions_are_parsed_without_akshare():
    response = MagicMock()
    response.json.return_value = {
        "records": [
            {
                "F020D": "2026-06-12",
                "F010N": 1,
                "F011N": 2,
                "F012N": 3.6,
            }
        ]
    }
    provider = CninfoProvider()
    provider._client = MagicMock()
    provider._client.post.return_value = response

    actions = provider.get_corporate_actions("000001.SZ")

    assert actions == [
        {
            "ex_date": date(2026, 6, 12),
            "action_type": "stock_split",
            "cash_per_share": Decimal("0.36"),
            "stock_ratio": Decimal("0.3"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        }
    ]
