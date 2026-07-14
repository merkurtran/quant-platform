from decimal import Decimal

from shared.market_data.tencent_provider import TencentProvider


def test_parse_minute_row_ignores_metadata_column_as_amount():
    row = [
        "202607141043",
        "1219.94",
        "1219.54",
        "1220.00",
        "1218.62",
        "43.00",
        {},
        "0.03",
    ]

    result = TencentProvider._parse_row(row)

    assert result["close"] == Decimal("1219.54")
    assert result["amount"] is None
