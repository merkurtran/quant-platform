import api from "@/lib/api";
import type {
  AIMessage,
  Conversation,
  SendMessageResponse,
  StockAnalysis,
  StockEventsResponse,
  StockNewsEvent,
  StrategyDraft,
} from "@/types";

export const aiService = {
  createConversation: () =>
    api.post<Conversation>("/ai/conversations", {}).then((r) => r.data),

  listConversations: () =>
    api.get<Conversation[]>("/ai/conversations").then((r) => r.data),

  listMessages: (conversationId: number, params?: { page?: number; page_size?: number }) =>
    api
      .get<AIMessage[]>(`/ai/conversations/${conversationId}/messages`, { params })
      .then((r) => r.data),

  sendMessage: (conversationId: number, content: string) =>
    api
      .post<SendMessageResponse>(`/ai/conversations/${conversationId}/messages`, {
        content,
      })
      .then((r) => r.data),

  getStockEvents: (symbol: string, stockName?: string | null) =>
    api
      .post<StockEventsResponse>(
        "/ai/stock-events",
        { symbol, stock_name: stockName || undefined },
        { timeout: 120000 }
      )
      .then((r) => r.data),

  analyzeStockEvent: (
    symbol: string,
    stockName: string | null | undefined,
    event: StockNewsEvent
  ) =>
    api
      .post<StockAnalysis>(
        "/ai/stock-analysis",
        { symbol, stock_name: stockName || undefined, event },
        { timeout: 120000 }
      )
      .then((r) => r.data),

  generateStrategyDraft: (description: string, name?: string) =>
    api
      .post<StrategyDraft>(
        "/ai/strategy-drafts",
        { description, name: name || undefined },
        { timeout: 120000 }
      )
      .then((r) => r.data),
};
