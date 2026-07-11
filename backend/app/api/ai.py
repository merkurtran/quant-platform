from fastapi import APIRouter, Depends

from app.core.exceptions import BizException, BizErrorCode
from app.core.config import get_settings
from app.core.rate_limiter import rate_limiter
from app.core.deps import get_current_user, get_async_db
from app.schemas.ai import (
    ConversationCreate,
    ConversationOut,
    MessageOut,
    SendMessageRequest,
    SendMessageResponse,
)
from app.ai.agent import handle_user_message

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


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

    settings = get_settings()
    allowed = await rate_limiter.check(
        f"llm:user:{user.id}", settings.llm.rate_limit_per_minute
    )
    if not allowed:
        raise BizException(
            BizErrorCode.RATE_LIMITED,
            f"Rate limit exceeded (max {settings.llm.rate_limit_per_minute} requests per minute)",
            status_code=429,
        )

    final_text = await handle_user_message(db, conversation_id, user.id, body.content)

    return SendMessageResponse(
        message_id=0,  # 前端从消息列表中获取
        role="assistant",
        content=final_text,
    )
