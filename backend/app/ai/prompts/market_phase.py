from app.ai.phase_guard import get_market_phase, PHASE_GUARD_PROMPTS

def build_phase_guard_prompt() -> str:
    """在每次对话的 system prompt 末尾注入当前市场阶段约束。
    参考 daily_stock_analysis phase_decision_guardrail 的设计：
    非交易日不得伪造盘中走势，盘前只能做开盘计划。"""
    phase = get_market_phase()
    guard = PHASE_GUARD_PROMPTS.get(phase, "")
    return f"\n\n[市场阶段约束] {guard}" if guard else ""
