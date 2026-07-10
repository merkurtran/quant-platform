from datetime import datetime
from typing import Optional

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
