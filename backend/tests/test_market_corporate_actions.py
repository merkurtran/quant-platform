from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from app.services.market_service import save_corporate_actions


def test_save_corporate_actions_merges_duplicate_constraint_keys():
    db = MagicMock()
    actions = [
        {
            "ex_date": date(2026, 4, 22),
            "action_type": "dividend",
            "cash_per_share": Decimal("2.178"),
            "stock_ratio": Decimal("0"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        },
        {
            "ex_date": date(2026, 4, 22),
            "action_type": "dividend",
            "cash_per_share": Decimal("4.779"),
            "stock_ratio": Decimal("0"),
            "rights_price": Decimal("0"),
            "rights_ratio": Decimal("0"),
        },
    ]

    save_corporate_actions(db, "300750.SZ", actions)

    statement = db.execute.call_args.args[0]
    parameters = statement.compile().params
    assert parameters["cash_per_share_m0"] == Decimal("6.957")
    assert parameters["symbol_m0"] == "300750.SZ"
