/** 业务错误码 — 与后端 BizErrorCode 对应 */
export const ErrorCode = {
  SUCCESS: 0,
  UNKNOWN: 10000,
  UNAUTHORIZED: 10001,
  TOKEN_EXPIRED: 10002,
  FORBIDDEN: 10003,
  NOT_FOUND: 20001,
  ALREADY_EXISTS: 20002,
  CONFLICT: 20003,
  ORDER_CANNOT_CANCEL: 20004,
  VALIDATION_ERROR: 30001,
  RATE_LIMITED: 40001,
  TRADE_FAILED: 40002,
  LLM_ERROR: 40003,
  BACKTEST_FAILED: 40004,
} as const;

/** API 基础配置 */
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";
export const WS_BASE_URL =
  process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000/ws/market";

/** K 线周期选项 */
export const PERIOD_OPTIONS = [
  { value: "1m", label: "1分" },
  { value: "5m", label: "5分" },
  { value: "15m", label: "15分" },
  { value: "30m", label: "30分" },
  { value: "60m", label: "60分" },
  { value: "1d", label: "日线" },
  { value: "1w", label: "周线" },
  { value: "1M", label: "月线" },
] as const;

/** 复权选项 */
export const ADJUST_OPTIONS = [
  { value: "qfq", label: "前复权" },
  { value: "none", label: "不复权" },
] as const;

/** 订单状态 */
export const ORDER_STATUS_LABELS: Record<string, string> = {
  pending: "待提交",
  submitted: "已提交",
  partial_filled: "部分成交",
  filled: "已成交",
  cancelled: "已撤销",
  rejected: "已拒绝",
};

/** 策略状态 */
export const STRATEGY_STATUS_LABELS: Record<string, string> = {
  draft: "草稿",
  backtested: "已回测",
  paper_running: "模拟运行",
  archived: "已归档",
};

/** 回测状态 */
export const BACKTEST_STATUS_LABELS: Record<string, string> = {
  queued: "排队中",
  running: "运行中",
  success: "成功",
  failed: "失败",
};

/** 告警规则类型 */
export const ALERT_RULE_TYPE_LABELS: Record<string, string> = {
  price_above: "价格上穿",
  price_below: "价格下穿",
  pct_change: "涨跌幅",
  volume_spike: "量异动",
  indicator: "指标触发",
};

/** 通知渠道 */
export const NOTIFY_CHANNEL_LABELS: Record<string, string> = {
  inapp: "站内",
  email: "邮件",
  webhook: "Webhook",
};

/** 侧边栏导航 */
export const NAV_ITEMS = [
  { href: "/market", label: "行情", icon: "CandlestickChart" },
  { href: "/strategies", label: "策略", icon: "Code2" },
  { href: "/trading/orders", label: "交易", icon: "ArrowLeftRight" },
  { href: "/alerts", label: "告警", icon: "Bell" },
  { href: "/ai", label: "AI 助手", icon: "Bot" },
] as const;
