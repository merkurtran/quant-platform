import backtrader as bt
import pandas as pd

from shared.strategy_sdk.base_strategy import BaseStrategy
from workers.strategy_worker.backtest_runner import _extract_strategy_class
from workers.strategy_worker.sandbox import build_restricted_globals


def test_sandbox_runs_standard_backtrader_indicator_namespace():
    restricted_globals = build_restricted_globals(BaseStrategy)
    exec(
        """
class SandboxStrategy(BaseStrategy):
    params = (('period', 2),)

    def __init__(self):
        self.sma = bt.indicators.SimpleMovingAverage(
            self.data.close,
            period=self.params.period,
        )
""",
        restricted_globals,
    )

    index = pd.date_range('2026-01-01', periods=3, freq='D')
    frame = pd.DataFrame(
        {
            'open': [10.0, 11.0, 12.0],
            'high': [11.0, 12.0, 13.0],
            'low': [9.0, 10.0, 11.0],
            'close': [10.5, 11.5, 12.5],
            'volume': [100, 120, 140],
        },
        index=index,
    )
    cerebro = bt.Cerebro()
    cerebro.adddata(bt.feeds.PandasData(dataname=frame))
    strategy_class = _extract_strategy_class(restricted_globals, BaseStrategy)
    cerebro.addstrategy(strategy_class)

    result = cerebro.run()

    assert len(result) == 1
