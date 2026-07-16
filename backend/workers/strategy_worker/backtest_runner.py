import platform
import sys
import io
import logging
import json
import time
import traceback
import multiprocessing
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Optional, List, Dict
from datetime import datetime

# ==================== 平台兼容性处理 ====================
IS_WINDOWS = platform.system() == "Windows"

if not IS_WINDOWS:
    # Unix/Linux/macOS 专属模块
    import resource
    import signal
else:
    # Windows 兼容性占位符
    resource = None  # type: ignore[assignment]
    signal = None     # type: ignore[assignment]

import backtrader as bt
import pandas as pd
import numpy as np
from sqlalchemy import func

from .code_analyzer import analyze_code_security, CodeSecurityError
from .sandbox import build_restricted_globals
from shared.strategy_sdk.base_strategy import BaseStrategy
from shared.db.session import SessionLocal 
from app.models.market import Klines
from app.services.market_service import get_klines_with_adjustment, AdjustMethod 
from app.services.a_share_trading_rules import AShareBacktestFiller, ASharePercentSizer

logger = logging.getLogger(__name__)

# 回测 worker 配置从 app.core.config.BacktestWorkerSettings 读取，
# 通过 .env 的 BACKTEST_WORKER__* 变量控制。


# ==================== 平台相关的资源限制函数 ====================

def _set_resource_limits():
    """
    设置操作系统级别的资源限制（仅 Linux/macOS 有效）

    Windows 环境下：
    - 内存限制：无法实现（无等价API），依赖进程级超时兜底
    - CPU 超时：由 multiprocessing.Process.join(timeout) 提供
    - 已知限制：记录到日志，不阻塞执行
    """
    from app.core.config import get_settings
    cfg = get_settings().backtest_worker

    if IS_WINDOWS:
        logger.warning(
            "Windows 环境：无法设置 OS 级资源限制 (rlimit/signal.alrm)。"
            "将使用进程级超时作为唯一防护手段。"
            "生产环境建议部署到 Linux/Docker。"
        )
        return
    
    try:
        # 内存限制 (字节)
        resource.setrlimit(
            resource.RLIMIT_AS,
            (cfg.max_memory_mb * 1024 * 1024, resource.RLIM_INFINITY)
        )
        # CPU 时间限制 (秒)
        resource.setrlimit(
            resource.RLIMIT_CPU,
            (cfg.max_cpu_seconds, cfg.max_cpu_seconds + 10)
        )
        # 文件大小限制 (10MB)
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (10 * 1024 * 1024, 10 * 1024 * 1024)
        )
        # 最大子进程数
        resource.setrlimit(
            resource.RLIMIT_NPROC,
            (32, 32)
        )
        logger.info(f"资源限制已设置: 内存={cfg.max_memory_mb}MB, CPU={cfg.max_cpu_seconds}s")
    except (ValueError, AttributeError) as e:
        logger.warning(f"设置资源限制失败: {e}")


def setup_timeout_handler(max_seconds: int):
    """设置超时信号处理器（仅 Unix 有效）"""
    if IS_WINDOWS:
        return  # Windows 不支持 SIGALRM
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"回测执行超时（最大允许时间: {max_seconds}秒）")
    
    try:
        signal.signal(signal.SIGALRM, timeout_handler)
        signal.alarm(max_seconds)
    except (OSError, ValueError) as e:
        logger.warning(f"设置信号超时失败: {e}")


# ==================== 数据类定义 ====================

@dataclass
class BacktestConfig:
    """回测配置"""
    strategy_code: str              # 用户上传的策略源码
    strategy_params: dict           # strategies.params JSONB
    symbol: str                     # 股票代码
    start_date: str                 # 回测开始日期 (YYYY-MM-DD)
    end_date: str                   # 回测结束日期 (YYYY-MM-DD)
    initial_capital: Decimal        # 初始资金
    run_id: int                     # 回测记录ID
    commission: float = 0.001       # 手续费率（千分之一）
    slippage: float = 0.0005        # 滑点率（万分之五）
    
    # 安全参数白名单
    ALLOWED_PARAM_TYPES = (str, int, float, bool, type(None))
    FORBIDDEN_PARAM_NAMES = {
        'self', 'cls', 'class', '__class__', '__init__',
        '__dict__', '__globals__', '__locals__',
        '__builtins__', '__import__',
    }
    
    def __post_init__(self):
        """验证并清理策略参数，防止注入攻击"""
        cleaned_params = {}
        for key, value in self.strategy_params.items():
            # 1. 过滤危险参数名
            if key in self.FORBIDDEN_PARAM_NAMES or key.startswith('_'):
                logger.warning(f"过滤危险参数名: {key}")
                continue
            
            # 2. 只允许安全类型
            if not isinstance(value, self.ALLOWED_PARAM_TYPES):
                try:
                    # 尝试转换为 JSON 安全类型
                    value = json.loads(json.dumps(value))
                    if not isinstance(value, self.ALLOWED_PARAM_TYPES):
                        logger.warning(f"参数 {key} 类型不安全，已跳过")
                        continue
                except (TypeError, ValueError):
                    logger.warning(f"参数 {key} 无法序列化，已跳过")
                    continue
            
            cleaned_params[key] = value
        
        self.strategy_params = cleaned_params
    
    def to_dict(self) -> dict:
        """转换为字典（用于日志记录）"""
        return {
            'symbol': self.symbol,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': str(self.initial_capital),
            'run_id': self.run_id,
            'commission': self.commission,
            'slippage': self.slippage,
            'strategy_params': self.strategy_params,
        }


@dataclass
class BacktestResult:
    """回测结果"""
    success: bool
    total_return: Optional[float] = None
    annual_return: Optional[float] = None
    max_drawdown: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    win_rate: Optional[float] = None
    trade_count: int = 0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    equity_curve: List[float] = field(default_factory=list)
    dates: List[str] = field(default_factory=list)
    trades: List[dict] = field(default_factory=list)
    error_message: Optional[str] = None
    error_type: Optional[str] = None
    execution_time_ms: int = 0
    cpu_time_ms: int = 0
    memory_used_mb: Optional[float] = None
    stdout_log: Optional[str] = None
    stderr_log: Optional[str] = None
    
    def to_dict(self) -> dict:
        """转换为字典（用于存储到数据库）"""
        return {
            'success': self.success,
            'total_return': self.total_return,
            'annual_return': self.annual_return,
            'max_drawdown': self.max_drawdown,
            'sharpe_ratio': self.sharpe_ratio,
            'win_rate': self.win_rate,
            'trade_count': self.trade_count,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'equity_curve': self.equity_curve,
            'dates': self.dates,
            'trades': self.trades,
            'error_message': self.error_message,
            'error_type': self.error_type,
            'execution_time_ms': self.execution_time_ms,
            'cpu_time_ms': self.cpu_time_ms,
            'memory_used_mb': self.memory_used_mb,
        }


# ==================== 自定义异常 ====================

class BacktestExecutionError(Exception):
    """回测执行错误"""
    pass


class TimeoutError(Exception):
    """执行超时"""
    pass


class StrategyClassNotFoundError(Exception):
    """未找到策略类"""
    pass


class DataLoadingError(Exception):
    """数据加载失败"""
    pass


# ==================== 核心执行函数 ====================

def _extract_strategy_class(restricted_globals: dict, base_class: type) -> type:
    """
    从全局命名空间提取用户定义的策略类
    
    安全规则：
    1. 优先寻找名为 'Strategy' 或 'MyStrategy' 的类
    2. 如果没有，取第一个继承自 base_class 的类
    3. 只允许一层继承（防止多层继承链滥用）
    4. 跳过私有/隐藏属性
    5. 跳过模块和函数
    """
    strategy_classes = []
    
    for name, obj in restricted_globals.items():
        # 跳过私有/隐藏属性
        if name.startswith('_'):
            continue
        
        # 跳过模块和函数
        if not isinstance(obj, type):
            continue
        
        # 检查是否继承自 BaseStrategy（但不包括 BaseStrategy 本身）
        try:
            if not issubclass(obj, base_class) or obj is base_class:
                continue
        except TypeError:
            # 不是类
            continue
        
        # 用户策略必须直接继承平台基类，避免通过多层继承绕过约束。
        if base_class not in obj.__bases__:
            logger.warning(f"策略类 {name} 必须直接继承 BaseStrategy")
            continue
        
        strategy_classes.append((name, obj))
    
    if not strategy_classes:
        raise StrategyClassNotFoundError("未找到继承自 BaseStrategy 的策略类")
    
    # 优先选择常见策略类名
    preferred_names = {'Strategy', 'MyStrategy', 'UserStrategy', 'MainStrategy'}
    for name, obj in strategy_classes:
        if name in preferred_names:
            logger.info(f"找到策略类: {name}")
            return obj
    
    # 返回第一个找到的策略类
    name, obj = strategy_classes[0]
    logger.info(f"使用策略类: {name}")
    return obj


def _load_kline_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    从数据库加载K线数据（带前复权处理）
    
    Args:
        symbol: 股票代码
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)
    
    Returns:
        DataFrame with columns: open, high, low, close, volume, datetime
        
    Raises:
        DataLoadingError: 数据加载失败
    """
    db = SessionLocal()
    
    try:
        kline_dicts = get_klines_with_adjustment(
            db=db,
            symbol=symbol,
            period='1d',
            limit=None,
            adjust=AdjustMethod.QFQ_RATIO,
            start=start_date,
            end=end_date,
        )
        
        if not kline_dicts:
            raise DataLoadingError(
                f"未找到 {symbol} 在 {start_date} ~ {end_date} 期间的日线数据"
            )
        
        # 转换为 backtrader 所需的 DataFrame 格式
        df = pd.DataFrame([{
            'open': float(k['open']),
            'high': float(k['high']),
            'low': float(k['low']),
            'close': float(k['close']),   # 这里已经是复权后的价格
            'volume': int(k['volume']) if k['volume'] else 0,
            'datetime': k['ts'],
        } for k in kline_dicts])
        
        df.set_index('datetime', inplace=True)
        listed_sessions_before_start = (
            db.query(func.count())
            .select_from(Klines)
            .filter(
                Klines.symbol == symbol,
                Klines.period == '1d',
                Klines.ts < kline_dicts[0]['ts'],
            )
            .scalar()
            or 0
        )
        df.attrs['listed_sessions_before_start'] = listed_sessions_before_start
        
        logger.info(
            f"加载 {symbol} 日线数据(前复权): {len(df)} 条, "
            f"范围: {df.index[0]} ~ {df.index[-1]}"
        )
        return df
        
    except DataLoadingError:
        raise
    except Exception as e:
        raise DataLoadingError(f"加载K线数据失败: {str(e)}")
    finally:
        db.close()


def _calculate_metrics(trade_analysis: dict) -> dict:
    """
    从 backtrader 交易分析结果中提取指标
    
    Returns:
        {
            'win_rate': float,
            'total_trades': int,
            'winning_trades': int,
            'losing_trades': int,
        }
    """
    # 总交易数
    total = trade_analysis.get('total', {})
    total_trades = total.get('total', 0)
    
    # 盈利交易
    won = trade_analysis.get('won', {})
    winning_trades = won.get('total', 0)
    
    # 亏损交易
    lost = trade_analysis.get('lost', {})
    losing_trades = lost.get('total', 0)
    
    # 胜率
    if total_trades > 0:
        win_rate = round((winning_trades / total_trades) * 100, 2)
    else:
        win_rate = None
    
    return {
        'win_rate': win_rate,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
    }


class _EquityCurveAnalyzer(bt.Analyzer):
    """Record portfolio value at the end of each processed bar."""

    def start(self):
        self.values = []
        self.dates = []

    def next(self):
        self.values.append(float(self.strategy.broker.getvalue()))
        self.dates.append(self.strategy.data.datetime.date(0).isoformat())

    def get_analysis(self):
        return {'values': self.values, 'dates': self.dates}


def _extract_equity_curve(strategy) -> tuple[List[float], List[str]]:
    """Extract the bar-by-bar portfolio value recorded during the run."""
    try:
        analysis = strategy.analyzers.equity_curve.get_analysis()
        return analysis.get('values', []), analysis.get('dates', [])
    except Exception as e:
        logger.warning(f"提取资金曲线失败: {e}")
        return [], []


def _extract_trades(strategy) -> List[dict]:
    """提取交易记录"""
    trades = []
    
    try:
        # 方法1：从 strategy.trades 获取
        if hasattr(strategy, 'trades'):
            for trade in strategy.trades:
                try:
                    trade_data = {
                        'entry_date': None,
                        'entry_price': None,
                        'exit_date': None,
                        'exit_price': None,
                        'size': None,
                        'pnl': None,
                    }
                    
                    if hasattr(trade, 'data') and hasattr(trade.data, 'datetime'):
                        # 入场
                        if hasattr(trade, 'dtopen'):
                            trade_data['entry_date'] = _format_date(trade.dtopen)
                        # 出场
                        if hasattr(trade, 'dtclose'):
                            trade_data['exit_date'] = _format_date(trade.dtclose)
                    
                    if hasattr(trade, 'price'):
                        trade_data['entry_price'] = float(trade.price)
                    if hasattr(trade, 'exitprice'):
                        trade_data['exit_price'] = float(trade.exitprice)
                    if hasattr(trade, 'size'):
                        trade_data['size'] = int(trade.size)
                    if hasattr(trade, 'pnl'):
                        trade_data['pnl'] = float(trade.pnl)
                    
                    trades.append(trade_data)
                except Exception as e:
                    logger.warning(f"提取单笔交易失败: {e}")
                    continue
    
    except Exception as e:
        logger.warning(f"提取交易列表失败: {e}")
    
    return trades


def _format_date(dt) -> str:
    """格式化日期"""
    if dt is None:
        return None
    if hasattr(dt, 'strftime'):
        return dt.strftime('%Y-%m-%d')
    return str(dt)


def _get_memory_usage() -> Optional[float]:
    """获取当前进程内存使用量（MB）"""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024
    except ImportError:
        return None
    except Exception:
        return None


def _calculate_simple_return(initial_value: float, final_value: float) -> float | None:
    if initial_value <= 0:
        return None
    return final_value / initial_value - 1


def _run_backtest_in_process(config: BacktestConfig) -> BacktestResult:
    """
    在子进程中实际执行的回测逻辑
    
    这个函数会运行在独立的子进程中，有资源限制保护
    """
    start_time = time.time()
    start_cpu_time = time.process_time()
    memory_start = _get_memory_usage()
    
    # 重定向 stdout/stderr
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    stdout_buffer = io.StringIO()
    stderr_buffer = io.StringIO()
    
    try:
        sys.stdout = stdout_buffer
        sys.stderr = stderr_buffer
        
        # ==================== 第1步: 安全检查 ====================
        try:
            analyze_code_security(config.strategy_code)
        except CodeSecurityError as e:
            return BacktestResult(
                success=False,
                error_message=str(e),
                error_type='CodeSecurityError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        
        # ==================== 第2步: 设置资源限制 ====================
        _set_resource_limits()
        from app.core.config import get_settings
        setup_timeout_handler(get_settings().backtest_worker.worker_timeout_seconds)
        
        # ==================== 第3步: 加载用户策略类 ====================
        restricted_globals = build_restricted_globals(BaseStrategy)
        
        try:
            # 执行用户代码
            exec(config.strategy_code, restricted_globals)
        except Exception as e:
            return BacktestResult(
                success=False,
                error_message=f"策略代码执行失败: {str(e)}",
                error_type='StrategyExecutionError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        
        try:
            UserStrategy = _extract_strategy_class(restricted_globals, BaseStrategy)
        except StrategyClassNotFoundError as e:
            return BacktestResult(
                success=False,
                error_message=str(e),
                error_type='StrategyClassNotFoundError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        
        # ==================== 第4步: 准备数据源 ====================
        try:
            df = _load_kline_data(config.symbol, config.start_date, config.end_date)
        except DataLoadingError as e:
            return BacktestResult(
                success=False,
                error_message=str(e),
                error_type='DataLoadingError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        
        # ==================== 第5步: 配置并运行回测 ====================
        try:
            cerebro = bt.Cerebro()
            
            # 添加数据源
            data = bt.feeds.PandasData(
                dataname=df,
                datetime='datetime' if 'datetime' in df.columns else None,
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
            )
            cerebro.adddata(data)
            
            # 添加策略（使用过滤后的参数）
            cerebro.addstrategy(UserStrategy, **config.strategy_params)
            cerebro.addsizer(ASharePercentSizer)
            
            # 配置经纪人
            cerebro.broker.setcash(float(config.initial_capital))
            cerebro.broker.setcommission(commission=config.commission)
            cerebro.broker.set_filler(
                AShareBacktestFiller(
                    config.symbol,
                    int(df.attrs.get('listed_sessions_before_start', 0)),
                )
            )
            if config.slippage:
                cerebro.broker.set_slippage_perc(config.slippage)
            
            # 添加分析器
            cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
            cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
            cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
            cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
            cerebro.addanalyzer(_EquityCurveAnalyzer, _name='equity_curve')
            
            # 运行回测
            results = cerebro.run()
            strat = results[0]
            
        except TimeoutError as e:
            return BacktestResult(
                success=False,
                error_message=str(e),
                error_type='TimeoutError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        except Exception as e:
            traceback.print_exc()
            return BacktestResult(
                success=False,
                error_message=f"回测运行失败: {str(e)}",
                error_type='BacktestRunError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
        
        # ==================== 第6步: 收集结果 ====================
        try:
            # 获取分析结果
            returns_analysis = strat.analyzers.returns.get_analysis()
            drawdown_analysis = strat.analyzers.drawdown.get_analysis()
            sharpe_analysis = strat.analyzers.sharpe.get_analysis()
            trades_analysis = strat.analyzers.trades.get_analysis()
            
            # 计算交易指标
            trade_metrics = _calculate_metrics(trades_analysis)
            
            # 提取资金曲线
            equity_values, equity_dates = _extract_equity_curve(strat)
            
            # 提取交易记录
            trade_list = _extract_trades(strat)
            
            # 计算执行时间
            execution_time = int((time.time() - start_time) * 1000)
            cpu_time = int((time.process_time() - start_cpu_time) * 1000)
            memory_end = _get_memory_usage()
            memory_used = None
            if memory_start is not None and memory_end is not None:
                memory_used = round(memory_end - memory_start, 2)
            
            # 构建结果
            return BacktestResult(
                success=True,
                total_return=_calculate_simple_return(
                    float(config.initial_capital),
                    float(cerebro.broker.getvalue()),
                ),
                annual_return=returns_analysis.get('rnorm'),
                max_drawdown=drawdown_analysis.get('max', {}).get('drawdown'),
                sharpe_ratio=sharpe_analysis.get('sharperatio'),
                win_rate=trade_metrics['win_rate'],
                trade_count=trade_metrics['total_trades'],
                total_trades=trade_metrics['total_trades'],
                winning_trades=trade_metrics['winning_trades'],
                losing_trades=trade_metrics['losing_trades'],
                equity_curve=equity_values,
                dates=equity_dates,
                trades=trade_list,
                execution_time_ms=execution_time,
                cpu_time_ms=cpu_time,
                memory_used_mb=memory_used,
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
            
        except Exception as e:
            return BacktestResult(
                success=False,
                error_message=f"收集回测结果失败: {str(e)}",
                error_type='ResultCollectionError',
                stdout_log=stdout_buffer.getvalue()[:10000],
                stderr_log=stderr_buffer.getvalue()[:10000],
            )
            
    except TimeoutError as e:
        return BacktestResult(
            success=False,
            error_message=str(e),
            error_type='TimeoutError',
            stdout_log=stdout_buffer.getvalue()[:10000],
            stderr_log=stderr_buffer.getvalue()[:10000],
        )
    except Exception as e:
        traceback.print_exc()
        return BacktestResult(
            success=False,
            error_message=f"回测执行异常: {str(e)}",
            error_type='UnknownError',
            stdout_log=stdout_buffer.getvalue()[:10000],
            stderr_log=stderr_buffer.getvalue()[:10000],
        )
    finally:
        # 恢复 stdout/stderr
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        # 取消超时定时器（仅 Unix）
        if not IS_WINDOWS:
            signal.alarm(0)


# ==================== 主入口函数 ====================

def _worker_process_main(config: BacktestConfig, queue) -> None:
    """
    工作进程的主函数
    """
    try:
        result = _run_backtest_in_process(config)
        queue.put(result)
    except Exception as e:
        # 捕获所有异常，防止子进程崩溃导致队列为空
        error_result = BacktestResult(
            success=False,
            error_message=f"工作进程异常: {str(e)}",
            error_type='WorkerProcessError',
        )
        queue.put(error_result)


def run_backtest(config: BacktestConfig) -> BacktestResult:
    """
    启动回测（主入口函数）
    
    使用多进程方式执行，确保主进程不受影响
    
    Args:
        config: 回测配置
    
    Returns:
        BacktestResult: 回测结果
    
    Example:
        >>> config = BacktestConfig(
        ...     strategy_code="...",
        ...     strategy_params={"param1": 10},
        ...     symbol="000001",
        ...     start_date="2023-01-01",
        ...     end_date="2023-12-31",
        ...     initial_capital=Decimal("100000"),
        ...     run_id=1,
        ... )
        >>> result = run_backtest(config)
        >>> if result.success:
        ...     print(f"总收益: {result.total_return:.2%}")
    """
    logger.info(f"启动回测: run_id={config.run_id}, symbol={config.symbol}")
    logger.debug(f"回测配置: {config.to_dict()}")
    
    start_time = time.time()
    process = None
    queue = None
    
    try:
        # 使用 spawn 上下文确保完全隔离
        ctx = multiprocessing.get_context('spawn')
        queue = ctx.Queue()
        process = ctx.Process(
            target=_worker_process_main,
            args=(config, queue),
            daemon=True,  # 主进程退出时自动终止
        )
        
        process.start()
        
        # 等待子进程完成（比 worker 内部超时多 15 秒）
        from app.core.config import get_settings
        process.join(timeout=get_settings().backtest_worker.process_join_timeout)
        
        # 检查子进程是否还在运行（超时）
        if process.is_alive():
            logger.warning(f"回测超时，强制终止进程: run_id={config.run_id}")
            process.terminate()
            process.join(timeout=5)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            return BacktestResult(
                success=False,
                error_message="回测执行超时（超过5分钟）",
                error_type='ProcessTimeoutError',
            )
        
        # 检查退出码
        if process.exitcode is not None and process.exitcode != 0:
            logger.error(f"回测进程异常退出: exitcode={process.exitcode}")
            return BacktestResult(
                success=False,
                error_message=f"回测进程异常退出 (exitcode={process.exitcode})",
                error_type='ProcessError',
            )
        
        # 获取结果
        if queue is not None and not queue.empty():
            result = queue.get_nowait()
            logger.info(f"回测完成: run_id={config.run_id}, success={result.success}, "
                       f"time={result.execution_time_ms}ms")
            return result
        
        return BacktestResult(
            success=False,
            error_message="未知错误：未能获取回测结果",
            error_type='UnknownError',
        )
        
    except multiprocessing.ProcessError as e:
        logger.error(f"多进程错误: {e}")
        return BacktestResult(
            success=False,
            error_message=f"进程错误: {str(e)}",
            error_type='ProcessError',
        )
    except Exception as e:
        logger.error(f"启动回测失败: {e}")
        traceback.print_exc()
        return BacktestResult(
            success=False,
            error_message=f"启动回测失败: {str(e)}",
            error_type='StartupError',
        )
    finally:
        # 清理资源
        if process is not None and process.is_alive():
            try:
                process.terminate()
                process.join(timeout=2)
                if process.is_alive():
                    process.kill()
            except Exception:
                pass
        
        # 清理队列
        if queue is not None:
            try:
                while not queue.empty():
                    queue.get_nowait()
            except Exception:
                pass


# ==================== 辅助函数（用于测试） ====================

def create_mock_config(**overrides) -> BacktestConfig:
    """创建测试用的模拟配置"""
    default_code = """
import backtrader as bt

class MyStrategy(BaseStrategy):
    params = (
        ('ma_period', 20),
    )
    
    def __init__(self):
        self.ma = bt.indicators.SMA(self.data.close, period=self.params.ma_period)
    
    def next(self):
        if not self.position:
            if self.data.close[0] > self.ma[0]:
                self.buy()
        else:
            if self.data.close[0] < self.ma[0]:
                self.sell()
    """
    
    defaults = {
        'strategy_code': default_code,
        'strategy_params': {'ma_period': 20},
        'symbol': '000001',
        'start_date': '2023-01-01',
        'end_date': '2023-12-31',
        'initial_capital': Decimal('100000'),
        'run_id': 1,
    }
    
    defaults.update(overrides)
    return BacktestConfig(**defaults)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    config = create_mock_config()
    result = run_backtest(config)
    
    print(f"Success: {result.success}")
    if result.success:
        print(f"Total Return: {result.total_return:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Max Drawdown: {result.max_drawdown:.2%}")
        print(f"Win Rate: {result.win_rate:.2f}%")
        print(f"Trade Count: {result.trade_count}")
        print(f"Execution Time: {result.execution_time_ms}ms")
    else:
        print(f"Error: {result.error_message}")
