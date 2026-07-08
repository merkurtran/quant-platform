"""统一日志配置"""
import logging
import sys

_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    """初始化根日志配置，输出到 stdout"""
    logging.basicConfig(
        level=level,
        format=_FORMAT,
        stream=sys.stdout,
    )


def get_logger(name: str) -> logging.Logger:
    """获取命名日志器"""
    return logging.getLogger(name)
