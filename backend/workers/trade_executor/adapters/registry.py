from typing import Callable

from .base import BrokerAdapter


_registry: dict[str, Callable[..., BrokerAdapter]] = {}

def register_adapter(broker_type: str, factory: Callable[..., BrokerAdapter]) -> None:
    _registry[broker_type] = factory

def get_adapter(broker_type: str, **kwargs) -> BrokerAdapter:
    if broker_type not in _registry:
        raise ValueError(f"Unknown broker type: {broker_type}")
    return _registry[broker_type](**kwargs)

# 注册 MockAdapter
from .mock_adapter import MockAdapter

def _mock_factory(**kwargs) -> MockAdapter:
    return MockAdapter(
        db_session_factory=kwargs["db_session_factory"],
        broker_account_id=kwargs["broker_account_id"],
    )

register_adapter("mock", _mock_factory)
