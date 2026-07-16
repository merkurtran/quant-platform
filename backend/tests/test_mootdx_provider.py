from unittest.mock import patch

from shared.market_data.mootdx_provider import MootdxProvider, _a_share_suffix


@patch("mootdx.quotes.Quotes.factory")
def test_configured_server_skips_automatic_probe(mock_factory, monkeypatch):
    monkeypatch.setenv("MOOTDX_SERVER", "110.41.147.114:7709")

    MootdxProvider()

    mock_factory.assert_called_once_with(
        market="std",
        server=("110.41.147.114", 7709),
    )


def test_a_share_filter_excludes_indices():
    assert _a_share_suffix("000001") == "SZ"
    assert _a_share_suffix("300750") == "SZ"
    assert _a_share_suffix("600519") == "SH"
    assert _a_share_suffix("688001") == "SH"
    assert _a_share_suffix("395001") is None
    assert _a_share_suffix("399001") is None
