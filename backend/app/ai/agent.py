import json
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_client import LLMClient
from app.ai.tools import TOOL_DEFINITIONS, execute_tool
from app.ai.prompts.market_phase import build_phase_guard_prompt
from app.models.ai import AIMessage
from app.models.trading import AuditLog

logger = logging.getLogger(__name__)

# 分级执行：自动执行 vs 需确认
AUTO_EXECUTE_TOOLS = {
    "generate_strategy_code", "review_strategy_code", "run_backtest",
    "interpret_backtest_result", "get_positions", "get_orders", "get_market_snapshot",
}
PAUSED_BY_DEFAULT = {"create_alert_rule"}  # 生成后默认暂停


SYSTEM_BASE = """你是 A 股量化交易助手。你可以：
- 根据描述生成 backtrader 策略代码
- 审查策略代码质量
- 解析自然语言预警规则
- 发起回测并解读结果
- 查询持仓、订单和行情

原则：
1. 所有生成类操作（策略/预警）自动保存为草稿/暂停状态，用户需手动确认后生效。
2. 回测解读提供量化指标和建议，不做买卖推荐。
3. 只读操作（查询持仓/订单/行情）直接执行。
4. 涉及真金白银的操作（启用预警、策略上线、真实下单）必须等用户明确确认。"""


async def handle_user_message(
    session: AsyncSession,
    conversation_id: int,
    user_id: int,
    message: str,
) -> str:
    """对话主循环：加载历史 → 追加用户消息 → Tool Use 循环 → 落库 → 返回最终回复。"""

    # 加载历史消息（最近 N 条，避免上下文溢出）
    MAX_HISTORY_MESSAGES = 50
    from sqlalchemy import select
    stmt = (
        select(AIMessage)
        .where(AIMessage.conversation_id == conversation_id)
        .order_by(AIMessage.created_at.desc())
        .limit(MAX_HISTORY_MESSAGES)
    )
    result = await session.execute(stmt)
    history = list(reversed(result.scalars().all()))

    # 构建 messages 列表
    messages = [{"role": "system", "content": SYSTEM_BASE + build_phase_guard_prompt()}]
    for h in history:
        role = h.role
        # tool 消息格式: {"role": "tool", "tool_call_id": ..., "content": ...}
        # assistant 消息可能带 tool_calls
        msg = {"role": h.role, "content": h.content.get("text", "") if role != "tool" else h.content.get("result", "")}
        if h.content.get("tool_calls"):
            msg["tool_calls"] = h.content["tool_calls"]
        if h.content.get("tool_call_id"):
            msg["tool_call_id"] = h.content["tool_call_id"]
        messages.append(msg)

    # 追加用户消息
    user_msg = {"role": "user", "content": message}
    messages.append(user_msg)

    # 落库用户消息
    db_user_msg = AIMessage(
        conversation_id=conversation_id,
        role="user",
        content={"text": message},
    )
    session.add(db_user_msg)
    await session.commit()

    # 对话循环
    llm = LLMClient()
    settings = get_settings()
    max_rounds = settings.llm.max_agent_rounds
    final_text = ""

    for _ in range(max_rounds):
        resp = await llm.chat(messages, tools=TOOL_DEFINITIONS)
        choice = resp["choices"][0]
        finish_reason = choice.get("finish_reason", "stop")

        if finish_reason == "tool_calls":
            assistant_msg = choice["message"]
            messages.append(assistant_msg)

            # 落库 assistant 消息（含 tool_calls）
            db_assist = AIMessage(
                conversation_id=conversation_id,
                role="assistant",
                content={
                    "tool_calls": assistant_msg.get("tool_calls", []),
                    "text": assistant_msg.get("content", ""),
                },
            )
            session.add(db_assist)
            await session.commit()

            for tc in assistant_msg.get("tool_calls", []):
                tool_name = tc["function"]["name"]
                tool_input = json.loads(tc["function"]["arguments"])

                # 执行工具
                tool_result = await execute_tool(
                    tool_name, tool_input, user_id, session
                )

                # 写审计日志
                audit = AuditLog(
                    user_id=user_id,
                    action=tool_name,
                    actor_type="ai_agent",
                    conversation_id=conversation_id,
                    detail={"input": tool_input, "output": tool_result},
                )
                session.add(audit)

                tool_msg = {
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(tool_result, ensure_ascii=False),
                }
                messages.append(tool_msg)

                # 落库 tool 消息
                db_tool = AIMessage(
                    conversation_id=conversation_id,
                    role="tool",
                    content={
                        "tool_name": tool_name,
                        "tool_input": tool_input,
                        "tool_result": tool_result,
                        "tool_call_id": tc["id"],
                    },
                )
                session.add(db_tool)

            await session.commit()
            continue  # 继续循环，把结果喂回模型

        # 正常结束
        final_text = choice["message"]["content"]

        db_assist = AIMessage(
            conversation_id=conversation_id,
            role="assistant",
            content={"text": final_text},
        )
        session.add(db_assist)
        await session.commit()
        break

    else:
        final_text = "处理超时，请简化您的问题后重试。"

    return final_text
