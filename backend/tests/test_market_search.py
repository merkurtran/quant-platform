import pandas as pd

from shared.market_data.akshare_provider import AKShareProvider


def test_search_stocks_uses_code_name_list(monkeypatch):
    stock_df = pd.DataFrame(
        [
            {"code": "600519", "name": "贵州茅台"},
            {"code": "000001", "name": "平安银行"},
        ]
    )
    monkeypatch.setattr(
        "shared.market_data.akshare_provider.ak.stock_info_a_code_name",
        lambda: stock_df,
    )
    AKShareProvider._spot_cache = {"df": None, "ts": 0.0}

    result = AKShareProvider().search_stocks("茅台")

    assert result == [{"symbol": "600519.SH", "name": "贵州茅台"}]
