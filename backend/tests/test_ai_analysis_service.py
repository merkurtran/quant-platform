import json

import pytest
from pydantic import SecretStr

from app.ai.analysis_service import AIAnalysisService, CACHE_TTL_SECONDS
from app.ai.llm_client import LLMClient, PROVIDER_CONFIG
from app.core.config import LLMSettings
from app.schemas.ai import (
    AnalyzeStockEventRequest,
    StockEventsRequest,
    StockNewsEvent,
    StrategyDraftRequest,
)


class FakeRedis:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.expirations: list[int] = []

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ex: int) -> None:
        self.values[key] = value
        self.expirations.append(ex)


class FakeLLM:
    provider = "claude"
    model = "test-model"

    def __init__(
        self,
        responses: list[dict | str],
        chat_responses: list[str] | None = None,
    ):
        self.responses = responses
        self.chat_responses = chat_responses or []
        self.web_search_calls = 0
        self.chat_calls = 0

    async def web_search(self, system: str, prompt: str, max_uses: int = 5) -> str:
        response = self.responses[self.web_search_calls]
        self.web_search_calls += 1
        return response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)

    async def chat(self, messages: list[dict], **kwargs) -> dict:
        content = self.chat_responses[self.chat_calls]
        self.chat_calls += 1
        return {"choices": [{"message": {"content": content}}]}


def analysis_payload() -> dict:
    return {
        "meta": {
            "symbol": "ignored",
            "stock_name": "ignored",
            "generated_at": "2026-07-14T00:00:00Z",
            "trigger": "ignored",
        },
        "sections": [
            {
                "id": "event_core",
                "title": "事件核心",
                "type": "card",
                "content": {"summary": "摘要", "impact": "影响"},
            },
            {
                "id": "topic_mapping",
                "title": "主题映射",
                "type": "table",
                "content": [],
            },
            {
                "id": "candidate_stocks",
                "title": "候选标的",
                "type": "table",
                "content": [],
            },
            {
                "id": "risk_checklist",
                "title": "风险清单",
                "type": "list",
                "content": [{"risk": "信息时效", "verification": "核验公告"}],
            },
        ],
        "disclaimer": "ignored",
        "sources": [
            {
                "title": "公告",
                "url": "https://example.com/source",
                "source_name": "示例来源",
                "published_at": "2026-07-14",
            }
        ],
    }


@pytest.mark.asyncio
async def test_stock_events_use_cache_without_second_llm_call():
    llm = FakeLLM(
        [
            {
                "events": [
                    {
                        "title": "公司发布公告",
                        "summary": "公告摘要",
                        "source_name": "交易所",
                        "source_url": "https://example.com/notice",
                        "published_at": "2026-07-14",
                    }
                ]
            }
        ]
    )
    service = AIAnalysisService(llm=llm, redis=FakeRedis())
    request = StockEventsRequest(symbol="600519.SH", stock_name="贵州茅台")

    first = await service.get_stock_events(request)
    second = await service.get_stock_events(request)

    assert first.cached is False
    assert second.cached is True
    assert second.events[0].title == "公司发布公告"
    assert llm.web_search_calls == 1
    assert service._redis.expirations == [CACHE_TTL_SECONDS]


def test_stock_cache_key_changes_on_next_shanghai_day(monkeypatch):
    service = AIAnalysisService(llm=FakeLLM([]), redis=FakeRedis())
    monkeypatch.setattr(service, "_cache_day", lambda: "2026-07-15")
    first_day = service._cache_key("events", "600519.SH")
    monkeypatch.setattr(service, "_cache_day", lambda: "2026-07-16")
    next_day = service._cache_key("events", "600519.SH")

    assert first_day != next_day
    assert CACHE_TTL_SECONDS == 86400


@pytest.mark.asyncio
async def test_no_recent_event_returns_automatic_web_analysis():
    llm = FakeLLM([{"events": []}, analysis_payload()])
    service = AIAnalysisService(llm=llm, redis=FakeRedis())

    result = await service.get_stock_events(
        StockEventsRequest(symbol="000001.SZ", stock_name="平安银行")
    )

    assert result.events == []
    assert result.auto_analysis is not None
    assert result.auto_analysis.meta.symbol == "000001.SZ"
    assert llm.web_search_calls == 2


def test_empty_llm_key_is_allowed_at_startup():
    settings = LLMSettings(api_key=SecretStr(""))
    assert settings.api_key.get_secret_value() == ""


def test_claude_message_conversion_preserves_tool_result():
    system, messages = LLMClient._to_claude_messages(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "question"},
            {
                "role": "assistant",
                "content": "",
                "tool_calls": [
                    {
                        "id": "tool-1",
                        "function": {"name": "lookup", "arguments": '{"x": 1}'},
                    }
                ],
            },
            {"role": "tool", "tool_call_id": "tool-1", "content": "result"},
        ]
    )

    assert system == "system"
    assert messages[1]["content"][0]["type"] == "tool_use"
    assert messages[2]["content"][0]["type"] == "tool_result"


def test_deepseek_has_official_anthropic_web_search_endpoint():
    assert (
        PROVIDER_CONFIG["deepseek"]["anthropic_base_url"]
        == "https://api.deepseek.com/anthropic"
    )


@pytest.mark.asyncio
async def test_stock_analysis_repairs_malformed_web_search_json():
    llm = FakeLLM(
        ["检索结果格式错误"],
        [json.dumps(analysis_payload(), ensure_ascii=False)],
    )
    service = AIAnalysisService(llm=llm, redis=FakeRedis())
    event = StockNewsEvent(
        event_id="event-1",
        title="公司公告",
        summary="公告摘要",
        source_name="交易所",
        source_url="https://example.com/notice",
    )

    result = await service.analyze_stock_event(
        AnalyzeStockEventRequest(
            symbol="600519.SH",
            stock_name="贵州茅台",
            event=event,
        )
    )

    assert result.meta.symbol == "600519.SH"
    assert [section.id for section in result.sections] == [
        "event_core",
        "topic_mapping",
        "candidate_stocks",
        "risk_checklist",
    ]
    assert llm.chat_calls == 1


@pytest.mark.asyncio
async def test_strategy_draft_repairs_and_validates_in_real_sandbox():
    invalid_code = "class InvalidStrategy:\n    pass"
    valid_code = """class MovingAverageStrategy(BaseStrategy):
    params = (
        ('fast_period', 5),
        ('slow_period', 20),
    )

    def __init__(self):
        self.fast = bt.indicators.SMA(self.data.close, period=self.params.fast_period)
        self.slow = bt.indicators.SMA(self.data.close, period=self.params.slow_period)
        self.cross = bt.indicators.CrossOver(self.fast, self.slow)

    def next(self):
        if not self.position and self.cross[0] > 0:
            self.buy()
        elif self.position and self.cross[0] < 0:
            self.sell()
"""
    llm = FakeLLM([], [invalid_code, valid_code])
    service = AIAnalysisService(llm=llm, redis=FakeRedis())

    result = await service.generate_strategy_draft(
        StrategyDraftRequest(description="五日均线上穿二十日均线买入，下穿卖出")
    )

    assert "MovingAverageStrategy" in result.code
    assert result.params == {"fast_period": 5, "slow_period": 20}
    assert llm.chat_calls == 2
