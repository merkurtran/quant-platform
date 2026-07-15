/** 统一 API 响应格式 */
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
  request_id: string;
}

// ── Auth ──

export interface UserPublic {
  id: number;
  email: string;
  nickname: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  expires_in: number;
  user: UserPublic;
}

// ── Market ──

export interface KlineItem {
  ts: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  amount: string | null;
}

export interface KlineListResponse {
  symbol: string;
  period: string;
  adjust: string;
  items: KlineItem[];
}

export interface WatchlistItem {
  symbol: string;
  name: string | null;
  sort_order: number;
  added_at: string;
}

export interface Watchlist {
  id: number;
  name: string;
  items: WatchlistItem[];
}

export interface StockSearchResult {
  symbol: string;
  name: string;
}

// ── Alerts ──

export type AlertRuleType =
  | "price_above"
  | "price_below"
  | "pct_change"
  | "volume_spike"
  | "indicator";

export interface AlertCondition {
  rule_type: AlertRuleType;
  value?: string;
  operator?: "gt" | "lt";
  baseline?: "previous_close" | "rule_created_price" | "custom";
  custom_baseline?: string;
  params?: Record<string, unknown>;
}

export interface AlertRule {
  id: number;
  symbol: string;
  rule_type: AlertRuleType;
  condition: AlertCondition;
  notify_channels: string[];
  status: "active" | "paused";
  created_at: string;
  last_triggered_at: string | null;
  last_triggered_price: string | null;
  dedup_cooldown_minutes: number | null;
  dedup_rearm_pct: string | null;
}

export interface AlertLog {
  id: number;
  triggered_at: string;
  trigger_value: string | null;
  message: string | null;
}

// ── Strategies ──

export interface Strategy {
  id: number;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StrategyDetail extends Strategy {
  code: string;
  params: Record<string, unknown>;
}

export interface BacktestRun {
  run_id: number;
  status: string;
}

export interface BacktestResultDetail {
  total_return: number | null;
  annual_return: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  win_rate: number | null;
  trade_count: number | null;
  equity_curve: Array<{ date: string; equity: number }> | null;
}

export interface BacktestRunResult {
  run_id: number;
  strategy_id: number;
  status: string;
  start_date: string;
  end_date: string;
  initial_capital: string;
  commission_rate: string;
  slippage_rate: string;
  symbols: string[];
  params_snapshot: Record<string, unknown>;
  created_at: string;
  finished_at: string | null;
  result: BacktestResultDetail | null;
  error_message: string | null;
}

export interface BacktestRunSummary {
  run_id: number;
  strategy_id: number;
  status: string;
  start_date: string;
  end_date: string;
  initial_capital: string;
  commission_rate: string;
  slippage_rate: string;
  symbols: string[];
  params_snapshot: Record<string, unknown>;
  created_at: string;
  finished_at: string | null;
  result: Pick<
    BacktestResultDetail,
    "total_return" | "max_drawdown" | "sharpe_ratio" | "trade_count"
  > | null;
  error_message: string | null;
}

// ── Trading ──

export interface BrokerAccount {
  id: number;
  broker_type: string;
  account_alias: string;
  status: string;
  initial_cash: string;
  cash_balance: string;
  commission_rate: string;
  minimum_commission: string;
  stamp_duty_rate: string;
  slippage_rate: string;
  created_at: string;
}

export interface Order {
  id: number;
  user_id: number;
  broker_account_id: number;
  strategy_id: number | null;
  client_order_id: string;
  symbol: string;
  side: "buy" | "sell";
  order_type: "limit" | "market";
  price: string | null;
  volume: string;
  filled_volume: string;
  filled_price: string | null;
  commission: string;
  stamp_duty: string;
  status: string;
  broker_order_id: string | null;
  origin: string;
  created_at: string;
  updated_at: string;
}

export interface Position {
  broker_account_id: number;
  symbol: string;
  volume: string;
  avg_cost: string;
  updated_at: string;
}

// ── AI ──

export interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
  updated_at: string;
}

export interface AIMessage {
  id: number;
  conversation_id: number;
  role: "user" | "assistant" | "tool";
  content: {
    text?: string;
    tool_calls?: Array<unknown>;
    tool_name?: string;
    tool_input?: unknown;
    tool_result?: unknown;
    tool_call_id?: string;
  };
  created_at: string;
}

export interface SendMessageResponse {
  message_id: number;
  role: string;
  content: string;
  tool_calls: Array<unknown> | null;
}

export interface EvidenceSource {
  title: string;
  url: string;
  source_name: string;
  published_at: string | null;
}

export interface StockNewsEvent {
  event_id: string;
  title: string;
  summary: string;
  source_name: string;
  source_url: string;
  published_at: string | null;
}

export interface AnalysisSection {
  id: "event_core" | "topic_mapping" | "candidate_stocks" | "risk_checklist";
  title: string;
  type: "card" | "table" | "list";
  content: Record<string, unknown> | Array<Record<string, unknown>>;
}

export interface StockAnalysis {
  meta: {
    symbol: string;
    stock_name: string | null;
    generated_at: string;
    trigger: string;
  };
  sections: AnalysisSection[];
  disclaimer: string;
  sources: EvidenceSource[];
  cached: boolean;
}

export interface StockEventsResponse {
  symbol: string;
  stock_name: string | null;
  events: StockNewsEvent[];
  auto_analysis: StockAnalysis | null;
  generated_at: string;
  cached: boolean;
}

export interface StrategyDraft {
  name: string;
  description: string;
  code: string;
  params: Record<string, unknown>;
}

// ── WebSocket ──

export interface QuoteMessage {
  symbol: string;
  price: number;
  previous_close?: number | null;
  change?: number | null;
  change_pct?: number | null;
  ts: string;
}

export interface AlertPushMessage {
  event: "alert";
  rule_id: number;
  symbol: string;
  rule_type: string;
  trigger_value: number;
  reason: string;
  triggered_at: string;
}
