from unittest.mock import MagicMock

from shared.market_data.fallback_provider import FallbackProvider


def test_symbol_sources_are_merged_and_normalized():
    primary = MagicMock()
    primary.get_all_symbols.return_value = ["600519.SH", "300750.SZ"]
    fallback = MagicMock()
    fallback.get_all_symbols.return_value = ["600519", "920001"]

    provider = FallbackProvider([primary, fallback])

    assert provider.get_all_symbols() == [
        "300750.SZ",
        "600519.SH",
        "920001.BJ",
    ]
