import builtins
from typing import Dict, Any

class SafeBuiltins:
    """安全的 builtins 封装器"""
    
    # 允许的内置函数
    ALLOWED_NAMES = {
        # 类型转换
        'int', 'float', 'str', 'bool', 
        'list', 'dict', 'tuple', 'set', 'complex',
        # 数学运算
        'abs', 'max', 'min', 'round', 'sum', 
        'pow', 'len', 'range', 'divmod',
        # 迭代工具
        'enumerate', 'zip', 'map', 'filter', 
        'sorted', 'reversed', 'iter', 'next',
        # 类型判断
        'isinstance', 'issubclass', 'hasattr', 
        'callable', 'type', 'super',
        # 常量
        'True', 'False', 'None', 
        'NotImplemented', 'Ellipsis',
        # 异常
        'Exception', 'ValueError', 'TypeError',
        'KeyError', 'IndexError', 'AttributeError',
        'StopIteration', 'RuntimeError', 'ZeroDivisionError',
        # 工具
        'repr', 'hash', 'dir', 'property',
        'classmethod', 'staticmethod', 'object', '__build_class__',
    }
    
    # 禁止访问的属性（防止绕过）
    FORBIDDEN_ATTRS = {
        '__builtins__', '__import__', '__loader__',
        '__spec__', '__file__', '__path__',
        '__class__', '__mro__', '__subclasses__',
        '__dict__', '__globals__', '__locals__',
        '__getattribute__', '__setattr__',
        '__call__', '__new__', '__init__',
    }
    
    def __init__(self):
        self._safe_builtins = {}
        for name in self.ALLOWED_NAMES:
            if hasattr(builtins, name):
                self._safe_builtins[name] = getattr(builtins, name)
    
    def __getitem__(self, key):
        return self._safe_builtins.get(key)
    
    def __contains__(self, key):
        return key in self._safe_builtins
    
    def get(self, key, default=None):
        return self._safe_builtins.get(key, default)


class SafeModuleProxy:
    """安全模块代理，限制对模块属性的访问"""
    
    def __init__(self, module, allowed_attrs: set, alias: str = None):
        self._module = module
        self._allowed_attrs = allowed_attrs
        self._alias = alias or module.__name__
    
    def __getattr__(self, name):
        if name in self._allowed_attrs:
            return getattr(self._module, name)
        raise AttributeError(f"Access to {self._alias}.{name} is not allowed")
    
    def __dir__(self):
        return list(self._allowed_attrs)


class SafeBacktraderProxy(SafeModuleProxy):
    """Expose Backtrader's indicator namespace without widening the sandbox."""

    def __init__(self, module, allowed_attrs: set, indicator_attrs: set):
        super().__init__(module, allowed_attrs | {'indicators'}, 'bt')
        self._safe_indicators = SafeModuleProxy(
            module.indicators,
            indicator_attrs,
            'bt.indicators',
        )

    def __getattr__(self, name):
        if name == 'indicators':
            return self._safe_indicators
        return super().__getattr__(name)


def build_restricted_globals(base_strategy_class) -> Dict[str, Any]:
    """
    构建安全的全局命名空间
    """
    import backtrader as bt
    import numpy as np
    import pandas as pd
    import math
    from datetime import datetime, timedelta
    from collections import namedtuple, defaultdict, Counter, OrderedDict
    from itertools import chain, combinations
    from typing import List, Dict, Tuple, Optional, Union, Any, Callable
    
    # 1. 安全的内置函数
    safe_builtins = SafeBuiltins()
    
    PD_ALLOWED = {
        # === 核心数据结构 ===
        'DataFrame', 'Series', 'Index',
        'MultiIndex', 'RangeIndex', 'CategoricalIndex',

        # === 创建/构造 ===
        'concat', 'merge', 'join',
        'pivot', 'pivot_table', 'melt', 'crosstab',
        'cut', 'qcut',

        # === 统计计算 ===
        'mean', 'median', 'mode', 'std', 'var',
        'sum', 'min', 'max', 'prod', 'cumsum',
        'count', 'nunique', 'value_counts',
        'describe', 'info', 'corr', 'cov',
        'rank', 'quantile', 'idxmax', 'idxmin',

        # === 数据清洗 ===
        'isna', 'notna', 'dropna', 'fillna',
        'drop_duplicates', 'duplicated',
        'replace', 'map', 'apply', 'applymap',
        'where', 'mask', 'clip', 'round',
        'astype', 'copy', 'sample', 'head', 'tail',

        # === 排序/索引 ===
        'sort_index', 'sort_values',
        'set_index', 'reset_index',
        'reindex', 'rename',

        # === 分组聚合 ===
        'groupby', 'rolling', 'expanding',
        'resample', 'transform', 'agg', 'aggregate',

        # === 时间序列 ===
        'to_datetime', 'to_timedelta', 'date_range',
        'period_range', 'timedelta_range',
        'tz_localize', 'tz_convert',

        # === 工具函数 ===
        'unique', 'factorize', 'get_dummies',
        'from_dict', 'from_records', 'DataFrame.from_arrays',
        'isnull', 'notnull',  # isna/notna 的别名
    }

    # 2. 限制 backtrader 模块访问
    BT_INDICATOR_ALLOWED = {
        'CrossOver', 'PercentChange', 'LogReturn',
        'SMA', 'SimpleMovingAverage',
        'EMA', 'ExponentialMovingAverage',
        'RSI', 'RelativeStrengthIndex',
        'MACD', 'BBands', 'BollingerBands',
        'ATR', 'AverageTrueRange',
        'Stochastic', 'WilliamsR', 'TRIX', 'CCI',
    }
    BT_ALLOWED = {
        # 核心类
        'Strategy', 'Indicator', 'Observer', 'Signal',
        'Line', 'LineSeries', 'LineBuffer', 
        # 方法
        'CrossOver', 'PercentChange', 'LogReturn',
        # 常用指标
        'SMA', 'EMA', 'RSI', 'MACD', 'BBands', 'ATR',
        'Stochastic', 'WilliamsR', 'TRIX', 'CCI',
        'AverageTrueRange', 'BollingerBands',
        # 观察器
        'Broker', 'Orders', 'Cash', 'Value',
        # 其他
        'date2num', 'num2date',
    }
    safe_bt = SafeBacktraderProxy(bt, BT_ALLOWED, BT_INDICATOR_ALLOWED)
    safe_pd = SafePandasProxy(pd, PD_ALLOWED, 'pd')
    # 3. 限制 numpy 模块访问
    NP_ALLOWED = {
        'array', 'zeros', 'ones', 'full', 'arange',
        'linspace', 'logspace', 'meshgrid',
        'random', 'mean', 'std', 'var', 'sum', 'prod',
        'min', 'max', 'argmin', 'argmax', 'argsort',
        'where', 'select', 'choose', 'clip',
        'concatenate', 'stack', 'vstack', 'hstack',
        'dot', 'matmul', 'tensordot',
        'eye', 'identity', 'diag',
        'allclose', 'isclose',
    }
    safe_np = SafeModuleProxy(np, NP_ALLOWED, 'np')
    
    return {
        '__builtins__': safe_builtins,
        '__name__': '__main__',
        
        # 策略框架
        'BaseStrategy': base_strategy_class,
        'bt': safe_bt,
        
        # 数据科学库
        'numpy': safe_np,
        'np': safe_np,
        'math': math,
        'pandas': safe_pd,
        'pd': safe_pd,
        
        # 日期时间
        'datetime': datetime,
        'timedelta': timedelta,
        
        # 集合/迭代工具
        'namedtuple': namedtuple,
        'defaultdict': defaultdict,
        'Counter': Counter,
        'OrderedDict': OrderedDict,
        'chain': chain,
        'combinations': combinations,
        
        # 类型注解
        'List': List,
        'Dict': Dict,
        'Tuple': Tuple,
        'Optional': Optional,
        'Union': Union,
        'Any': Any,
        'Callable': Callable,
    }


class SafePandasProxy(SafeModuleProxy):
    """
    带黑名单拦截的 pandas 安全代理
    
    在 SafeModuleProxy 白名单基础上，额外拦截已知高危方法。
    即使方法在白名单中，如果出现在黑名单里也会被拒绝。
    
    第一阶段（最低限度防护）：明确排除 IO / 反序列化 / 表达式执行类方法
    后续可演进为完整白名单模式。
    """

    # 已知的高危方法黑名单（优先级高于白名单）
    PANDAS_FORBIDDEN = frozenset({
        # === 反序列化类（RCE 风险）===
        'read_pickle',                    # pd.read_pickle → 任意代码执行
        'to_pickle',                      # DataFrame.to_pickle → 写入恶意数据
        
        # === 文件读写类 ===
        'read_csv',                       # 读取任意文件
        'to_csv',                         # 写入任意文件
        'read_table',                     # 同 read_csv 变体
        'read_fwf',                       # 固定宽度格式读取
        'read_excel',                     # Excel 文件读写
        'to_excel',
        'read_json',                      # JSON 文件读写
        'to_json',
        'read_html',                      # HTML 表格解析
        'to_html',
        'read_xml',
        'to_xml',
        'read_clipboard',                 # 剪贴板操作
        'to_clipboard',
        'read_feather',                   # Feather 格式
        'to_feather',
        'read_orc',                       # ORC 格式
        'to_orc',
        'read_parquet',                   # Parquet 文件
        'to_parquet',
        'read_sas',                       # SAS 数据集
        'read_spss',                      # SPSS 数据集
        'read_stata',                     # Stata 数据集
        'to_stata',
        
        # === HDF5 相关（文件+反序列化）===
        'HDFStore',                       # HDF5 存储引擎
        'read_hdf',                       # 从 HDF5 读取
        'to_hdf',                         # 写入 HDF5
        'HDFStore.put',                   # 内部 put 方法
        'HDFStore.get',                   # 内部 get 方法
        
        # === SQL 数据库相关 ===
        'read_sql',                       # SQL 查询（可能被注入）
        'read_sql_query',
        'read_sql_table',
        'to_sql',
        
        # === 表达式执行类 ===
        'eval',                           # DataFrame.eval() → 任意表达式
        'query',                          # DataFrame.query() → 任意表达式
        
        # === 网络相关 ===
        'read_gbq',                       # Google BigQuery（网络请求）
    })

    def __init__(self, module, allowed_attrs: set, alias: str = 'pd'):
        super().__init__(module, allowed_attrs, alias)

    def __getattr__(self, name):
        # 黑名单优先：即使白名单允许，黑名单里的也要拦截
        if name in self.PANDAS_FORBIDDEN:
            raise AttributeError(
                f"Access to {self._alias}.{name} is forbidden (security risk)"
            )
        return super().__getattr__(name)
