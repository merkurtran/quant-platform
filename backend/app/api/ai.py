import logging
from collections.abc import Awaitable
from typing import TypeVar

from fastapi import APIRouter, Depends

from app.core.exceptions import BizException, BizErrorCode
from app.core.config import get_settings
from app.core.rate_limiter import rate_limiter
from app.core.deps import get_current_user, get_async_db
from app.schemas.ai import (
    AnalyzeStockEventRequest,
    ConversationOut,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
    StockAnalysisResponse,
    StockEventsRequest,
    StockEventsResponse,
    StrategyDraftRequest,
    StrategyDraftResponse,
)
from app.ai.agent import handle_user_message
from app.ai.analysis_service import AIAnalysisService
from app.ai.llm_client import LLMConfigurationError

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = logging.getLogger(__name__)
T = TypeVar("T")


async def _check_ai_rate_limit(user_id: int) -> None:
    settings = get_settings()
    allowed = await rate_limiter.check(
        f"llm:user:{user_id}", settings.llm.rate_limit_per_minute
    )
    if not allowed:
        raise BizException(
            BizErrorCode.RATE_LIMITED,
            f"Rate limit exceeded (max {settings.llm.rate_limit_per_minute} requests per minute)",
            status_code=429,
        )


async def _run_ai(operation: Awaitable[T]) -> T:
    try:
        return await operation
    except LLMConfigurationError as exc:
        raise BizException(
            BizErrorCode.LLM_ERROR, str(exc), status_code=503
        ) from exc
    except Exception as exc:
        logger.exception("AI request failed")
        raise BizException(
            BizErrorCode.LLM_ERROR,
            "AI 服务暂时不可用，请稍后重试",
            status_code=502,
        ) from exc


@router.post("/conversations", response_model=ConversationOut)
async def create_conversation(
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from app.models.ai import AIConversation

    conv = AIConversation(user_id=user.id)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.ai import AIConversation

    stmt = (
        select(AIConversation)
        .where(AIConversation.user_id == user.id)
        .order_by(AIConversation.updated_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
async def list_messages(
    conversation_id: int,
    page: int = 1,
    page_size: int = 50,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from sqlalchemy import select
    from app.models.ai import AIConversation, AIMessage

    conv = await db.get(AIConversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise BizException(BizErrorCode.NOT_FOUND, "Conversation not found", status_code=404)

    stmt = (
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
)
async def send_message(
    conversation_id: int,
    body: SendMessageRequest,
    db=Depends(get_async_db),
    user=Depends(get_current_user),
):
    from app.models.ai import AIConversation

    conv = await db.get(AIConversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise BizException(BizErrorCode.NOT_FOUND, "Conversation not found", status_code=404)

    await _check_ai_rate_limit(user.id)

    final_text = await _run_ai(
        handle_user_message(db, conversation_id, user.id, body.content)
    )

    return SendMessageResponse(
        message_id=0,  # 前端从消息列表中获取
        role="assistant",
        content=final_text,
    )


@router.post("/stock-events", response_model=StockEventsResponse)
async def get_stock_events(
    body: StockEventsRequest,
    user=Depends(get_current_user),
):
    await _check_ai_rate_limit(user.id)
    return await _run_ai(AIAnalysisService().get_stock_events(body))


@router.post("/stock-analysis", response_model=StockAnalysisResponse)
async def analyze_stock_event(
    body: AnalyzeStockEventRequest,
    user=Depends(get_current_user),
):
    await _check_ai_rate_limit(user.id)
    return await _run_ai(AIAnalysisService().analyze_stock_event(body))


@router.post("/strategy-drafts", response_model=StrategyDraftResponse)
async def generate_strategy_draft(
    body: StrategyDraftRequest,
    user=Depends(get_current_user),
):
    await _check_ai_rate_limit(user.id)
    return await _run_ai(AIAnalysisService().generate_strategy_draft(body))
