from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from app.core.config import get_settings

_MSG_MAX_LENGTH: int = get_settings().llm.message_max_length


class ConversationCreate(BaseModel):
    pass  # 新建对话无需额外参数


class ConversationOut(BaseModel):
    id: int
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str = Field(min_length=1, max_length=_MSG_MAX_LENGTH)


class SendMessageResponse(BaseModel):
    message_id: int
    role: str
    content: str
    tool_calls: Optional[list[dict]] = None


class EvidenceSource(BaseModel):
    title: str
    url: str
    source_name: str
    published_at: Optional[str] = None


class StockNewsEvent(BaseModel):
    event_id: str
    title: str
    summary: str
    source_name: str
    source_url: str
    published_at: Optional[str] = None


class AnalysisMeta(BaseModel):
    symbol: str
    stock_name: Optional[str] = None
    generated_at: datetime
    trigger: str


class AnalysisSection(BaseModel):
    id: Literal[
        "event_core",
        "topic_mapping",
        "candidate_stocks",
        "risk_checklist",
    ]
    title: str
    type: Literal["card", "table", "list"]
    content: dict[str, Any] | list[Any]


class StockAnalysisResponse(BaseModel):
    meta: AnalysisMeta
    sections: list[AnalysisSection]
    disclaimer: str
    sources: list[EvidenceSource]
    cached: bool = False


class StockEventsRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    stock_name: Optional[str] = Field(default=None, max_length=100)


class StockEventsResponse(BaseModel):
    symbol: str
    stock_name: Optional[str] = None
    events: list[StockNewsEvent]
    auto_analysis: Optional[StockAnalysisResponse] = None
    generated_at: datetime
    cached: bool = False


class AnalyzeStockEventRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    stock_name: Optional[str] = Field(default=None, max_length=100)
    event: StockNewsEvent


class StrategyDraftRequest(BaseModel):
    description: str = Field(min_length=5, max_length=2000)
    name: Optional[str] = Field(default=None, max_length=100)


class StrategyDraftResponse(BaseModel):
    name: str
    description: str
    code: str
    params: dict[str, Any]
