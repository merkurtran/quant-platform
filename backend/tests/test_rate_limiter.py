from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core import rate_limiter as rate_limiter_module


@pytest.mark.asyncio
async def test_rate_limiter_uses_pooled_async_client(monkeypatch):
    redis_client = MagicMock()
    redis_client.eval = AsyncMock(return_value=1)
    monkeypatch.setattr(
        rate_limiter_module,
        "get_async_redis_client",
        lambda: redis_client,
    )

    allowed = await rate_limiter_module.RateLimiter().check("test:user:1", limit=5)

    assert allowed is True
    redis_client.eval.assert_awaited_once()
