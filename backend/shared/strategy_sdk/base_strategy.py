import backtrader as bt


class BaseStrategy(bt.Strategy):
    """
    所有用户上传的策略都应该继承此基类，而非直接继承 bt.Strategy。
    
    ## 设计原则
    - **轻薄封装**: 本质上就是 backtrader 原生策略，仅添加约定和工具方法
    - **统一收口**: 未来新增全局行为（风控、日志、监控）只需改此基类
    - **命名约定**: 强制规范 params/生命周期方法，便于与数据库字段映射
    
    ## 用户使用示例
    
    ```python
    from shared.strategy_sdk.base_strategy import BaseStrategy
    
    class MyStrategy(BaseStrategy):
        # 必须定义 params（会自动映射到 strategies.params JSONB 字段）
        params = (
            ('period', 20),           # 移动平均周期
            ('threshold', 0.02),      # 阈值
        )
        
        def __init__(self):
            # 初始化指标
            self.sma = bt.indicators.SMA(self.data.close, period=self.params.period)
        
        def next(self):
            # 核心交易逻辑
            if not self.position:
                if self.data.close[0] > self.sma[0]:
                    self.buy()
            else:
                if self.data.close[0] < self.sma[0]:
                    self.close()
    
    ```
    
    ## 必须遵守的约定
    
    ### 1. params 类属性 (必须)
    - 类型: tuple of tuples
    - 用途: 策略可配置参数，自动序列化到 `strategies.params` JSONB 字段
    - 示例: `params = (('period', 20), ('threshold', 0.02))`
    
    ### 2. 数据源访问
    - 使用 `self.data` 或 `self.datas[0]` 访问主数据源
    - 支持多数据源时使用 `self.data1`, `self.data2` ...
    
    ### 3. 生命周期方法 (可选重写)
    - `__init__()`: 初始化指标
    - `next()`: 每根K线触发的主逻辑
    - `notify_order(order)`: 订单状态变化通知
    - `notify_trade(trade)`: 交易完成通知
    - `notify_cashvalue(cash, value)`: 账户价值变化通知
    - `start()` / `stop()`: 策略开始/结束时的钩子

    ### 4. 默认仓位
    - 回测引擎默认使用 95% 可用资金，并按 A 股 100 股整手下单
    - 调用 `self.buy(size=...)` 可覆盖默认仓位
    """

    # ==================== 工具方法 ====================

    def log(self, message: str, dt=None) -> None:
        """统一日志输出"""
        dt = dt or self.datas[0].datetime.date(0)
        print(f"{dt.isoformat()} {self.__class__.__name__} | {message}")

    def get_param(self, name: str, default=None):
        """安全获取参数值（带默认值）"""
        return getattr(self.params, name, default)

    def current_price(self) -> float:
        """获取当前收盘价"""
        return self.data.close[0]

    def position_size(self) -> float:
        """获取当前持仓数量"""
        return self.position.size if self.position else 0.0

    # ==================== 生命周期钩子 (可重写) ====================

    def notify_order(self, order):
        """订单状态变化通知（已提供基础实现）"""
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(
                    f'BUY EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}'
                )
            else:
                self.log(
                    f'SELL EXECUTED, Price: {order.executed.price:.2f}, '
                    f'Cost: {order.executed.value:.2f}, Comm {order.executed.comm:.2f}'
                )
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

    def notify_trade(self, trade):
        """交易完成通知（记录盈亏）"""
        if not trade.isclosed:
            return

        self.log(
            f'TRADE CLOSED, PnL: {trade.pnl:.2f}, Net PnL: {trade.pnlcomm:.2f}'
        )

    def notify_cashvalue(self, cash, value):
        """账户价值变化（可选启用，用于调试）"""
        # 默认不输出（避免日志过多），子类可重写启用
        pass

    def stop(self):
        """策略结束时的最终统计"""
        self.log(
            f'(Final) Portfolio Value: {self.broker.getvalue():.2f}, '
            f'Cash: {self.broker.getcash():.2f}'
        )
