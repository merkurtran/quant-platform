from datetime import date
from decimal import Decimal
from unittest.mock import patch

import pandas as pd

from shared.market_data.akshare_provider import AKShareProvider


def test_get_corporate_actions_returns_dividends_and_rights_issues():
    dividends = pd.DataFrame(
        [
            {
                "\u9664\u6743\u65e5": "2026-06-12",
                "\u9001\u80a1\u6bd4\u4f8b": 1,
                "\u8f6c\u589e\u6bd4\u4f8b": 0,
                "\u6d3e\u606f\u6bd4\u4f8b": 3.6,
            }
        ]
    )
    rights_issues = pd.DataFrame(
        [
            {
                "\u9664\u6743\u65e5": "2026-07-01",
                "\u914d\u80a1\u65b9\u6848": 2,
                "\u914d\u80a1\u4ef7\u683c": 8,
            }
        ]
    )

    with (
        patch(
            "shared.market_data.akshare_provider.ak.stock_dividend_cninfo",
            return_value=dividends,
        ),
        patch(
            "shared.market_data.akshare_provider.ak.stock_history_dividend_detail",
            return_value=rights_issues,
        ),
    ):
        actions = AKShareProvider().get_corporate_actions("000001.SZ")

    assert actions == [
        {
            "ex_date": date(2026, 6, 12),
            "action_type": "stock_split",
            "cash_per_share": Decimal("0.36"),
            "stock_ratio": Decimal("0.1"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        },
        {
            "ex_date": date(2026, 7, 1),
            "action_type": "rights_issue",
            "cash_per_share": Decimal("0"),
            "stock_ratio": Decimal("0"),
            "rights_price": Decimal("8"),
            "rights_ratio": Decimal("0.2"),
        },
    ]
