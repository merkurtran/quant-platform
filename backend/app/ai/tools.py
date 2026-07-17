import json
from typing import Any

from app.ai.prompts.strategy_gen import STRATEGY_GEN_SYSTEM
from app.ai.prompts.backtest_interpret import BACKTEST_INTERPRET_SYSTEM
from app.ai.prompts.code_review import CODE_REVIEW_SYSTEM
from app.ai.llm_client import LLMClient
from app.core.config import get_settings


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "generate_strategy_code",
            "description": "根据自然语言描述生成 A 股量化策略 Python 代码（backtrader 框架），保存为策略草稿。",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "策略的自然语言描述，如'5日均线上穿20日均线买入，下穿卖出'",
                    },
                    "name": {
                        "type": "string",
                        "description": "策略名称，不超过128字",
                    },
                },
                "required": ["description", "name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "review_strategy_code",
            "description": "审查已有策略代码的逻辑漏洞、风险点和边界条件问题。",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {
                        "type": "integer",
                        "description": "要审查的策略 ID",
                    },
                },
                "required": ["strategy_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_alert_rule",
            "description": "根据自然语言设置价格/涨跌幅/成交量预警规则，默认创建为暂停状态，需用户手动启用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "raw_text": {
                        "type": "string",
                        "description": "自然语言预警描述，如'茅台跌破1600提醒我'",
                    },
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 600519.SH",
                    },
                },
                "required": ["raw_text", "symbol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_backtest",
            "description": "对指定策略发起回测。",
            "parameters": {
                "type": "object",
                "properties": {
                    "strategy_id": {"type": "integer"},
                    "symbols": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "股票代码列表",
                    },
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "initial_capital": {
                        "type": "number",
                        "description": "初始资金，默认 1000000",
                    },
                },
                "required": ["strategy_id", "symbols", "start_date", "end_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "interpret_backtest_result",
            "description": "解读回测报告，给出自然语言总结和优化建议。",
            "parameters": {
                "type": "object",
                "properties": {
                    "run_id": {
                        "type": "integer",
                        "description": "回测运行 ID",
                    },
                },
                "required": ["run_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_positions",
            "description": "查询当前用户持仓快照。",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_orders",
            "description": "查询当前用户订单列表，可按状态过滤。",
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "订单状态过滤：pending/submitted/filled/cancelled/rejected",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_market_snapshot",
            "description": "查询指定股票最新行情快照（价格、涨跌幅、成交量）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票代码，如 600519.SH",
                    },
                },
                "required": ["symbol"],
            },
        },
    },
]


async def execute_tool(
    tool_name: str,
    tool_input: dict,
    user_id: int,
    db_session,
) -> dict:
    """工具执行分发。映射到 services/ 层已有函数，AI 和人工走同一路径。"""
    from app.services import strategy_service, alert_service, order_service, market_service
    from app.ai.llm_client import LLMClient

    match tool_name:
        case "generate_strategy_code":
            code = await _gen_strategy_code(tool_input)
            strategy = await strategy_service.create_strategy(
                db_session,
                user_id=user_id,
                name=tool_input["name"],
                description=tool_input["description"],
                code=code,
                params={},
            )
            return {"strategy_id": strategy.id, "status": "draft"}

        case "review_strategy_code":
            strategy = await strategy_service.get_strategy(
                db_session, tool_input["strategy_id"], user_id
            )
            if strategy is None:
                return {"error": "Strategy not found"}
            review = await _gen_code_review(strategy.code)
            return {"issues": review}

        case "create_alert_rule":
            parsed = await _parse_alert(tool_input["raw_text"], tool_input["symbol"])
            rule = await alert_service.create_rule(
                db_session,
                user_id=user_id,
                symbol=tool_input["symbol"],
                rule_type=parsed["rule_type"],
                condition=parsed["condition"],
                notify_channels=["inapp"],
            )
            # 创建后立即设为暂停，等用户确认
            await alert_service.update_rule_status(db_session, rule.id, "paused")
            return {"rule_id": rule.id, "status": "paused", "parsed": parsed}

        case "run_backtest":
            bt = await strategy_service.create_backtest(
                db_session,
                user_id=user_id,
                strategy_id=tool_input["strategy_id"],
                symbols=tool_input["symbols"],
                start_date=tool_input["start_date"],
                end_date=tool_input["end_date"],
                initial_capital=tool_input.get(
                "initial_capital",
                get_settings().trading.default_backtest_capital,
            ),
            )
            return {"run_id": bt.run_id, "status": "queued"}

        case "interpret_backtest_result":
            from app.services import strategy_service as ss
            result = await ss.get_backtest_result(db_session, tool_input["run_id"])
            if result is None:
                return {"error": "Backtest result not found"}
            interpretation = await _gen_backtest_interpret(result)
            return {"interpretation": interpretation}

        case "get_positions":
            positions = await order_service.get_positions_by_user(db_session, user_id)
            return {
                "positions": [
                    {"symbol": p.symbol, "volume": float(p.volume), "avg_cost": float(p.avg_cost)}
                    for p in positions
                ]
            }

        case "get_orders":
            status = tool_input.get("status")
            orders, _ = await order_service.get_orders(
                db_session, user_id, status=status
            )
            return {
                "orders": [
                    {
                        "id": o.id,
                        "symbol": o.symbol,
                        "side": o.side,
                        "price": float(o.price) if o.price else None,
                        "volume": float(o.volume),
                        "status": o.status,
                    }
                    for o in orders
                ]
            }

        case "get_market_snapshot":
            snap = await market_service.get_snapshot(db_session, tool_input["symbol"])
            return snap if snap else {"error": "No data available"}

        case _:
            return {"error": f"Unknown tool: {tool_name}"}


# ── LLM 子任务：生成策略代码 ──
async def _gen_strategy_code(params: dict) -> str:
    llm = LLMClient()
    messages = [
        {"role": "system", "content": STRATEGY_GEN_SYSTEM},
        {"role": "user", "content": params["description"]},
    ]
    resp = await llm.chat(messages, temperature=0.2, max_tokens=2048)
    content = resp["choices"][0]["message"]["content"]
    # 提取代码块
    if "```python" in content:
        start = content.index("```python") + len("```python")
        end = content.index("```", start)
        return content[start:end].strip()
    return content.strip()


# ── LLM 子任务：代码审查 ──
async def _gen_code_review(code: str) -> list[dict]:
    llm = LLMClient()
    messages = [
        {"role": "system", "content": CODE_REVIEW_SYSTEM},
        {"role": "user", "content": code},
    ]
    resp = await llm.chat(messages, temperature=0.1, max_tokens=1024)
    content = resp["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return [{"severity": "info", "message": content}]


# ── LLM 子任务：回测解读 ──
async def _gen_backtest_interpret(result: dict) -> str:
    llm = LLMClient()
    context = json.dumps(
        {
            "total_return": result.get("total_return"),
            "max_drawdown": result.get("max_drawdown"),
            "sharpe_ratio": result.get("sharpe_ratio"),
            "win_rate": result.get("win_rate"),
            "trade_count": result.get("trade_count"),
        },
        ensure_ascii=False,
    )
    messages = [
        {"role": "system", "content": BACKTEST_INTERPRET_SYSTEM},
        {"role": "user", "content": context},
    ]
    resp = await llm.chat(messages, temperature=0.3, max_tokens=1024)
    return resp["choices"][0]["message"]["content"]


# ── LLM 子任务：预警解析 ──
async def _parse_alert(raw_text: str, symbol: str) -> dict:
    llm = LLMClient()
    messages = [
        {"role": "system", "content": _ALERT_PARSE_SYSTEM},
        {"role": "user", "content": raw_text},
    ]
    resp = await llm.chat(messages, temperature=0.0, max_tokens=256)
    content = resp["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"rule_type": "price_below", "condition": {"operator": "<", "value": 0}}


_ALERT_PARSE_SYSTEM = """将自然语言预警描述解析为结构化规则，输出 JSON：
{"rule_type": "price_above|price_below|pct_change|volume_spike", "condition": {"operator": ">|<|>=", "value": number}}
仅输出 JSON，无需解释。"""
