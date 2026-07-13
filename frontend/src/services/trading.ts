import api from "@/lib/api";
import type { BrokerAccount, Order, Position } from "@/types";

export const tradingService = {
  // 券商账户
  listAccounts: () =>
    api.get<BrokerAccount[]>("/broker_accounts").then((r) => r.data),

  createAccount: (data: { broker_type?: string; account_alias: string }) =>
    api.post<BrokerAccount>("/broker_accounts", data).then((r) => r.data),

  deleteAccount: (accountId: number) =>
    api.delete(`/broker_accounts/${accountId}`),

  // 订单
  listOrders: (params?: {
    status?: string;
    symbol?: string;
    strategy_id?: number;
    page?: number;
    page_size?: number;
  }) => api.get<Order[]>("/orders", { params }).then((r) => r.data),

  createOrder: (data: {
    broker_account_id: number;
    symbol: string;
    side: "buy" | "sell";
    order_type?: "limit" | "market";
    price?: string;
    volume: string;
  }) => api.post<Order>("/orders", data).then((r) => r.data),

  cancelOrder: (orderId: number) =>
    api.delete<Order>(`/orders/${orderId}`).then((r) => r.data),

  // 持仓
  listPositions: () =>
    api.get<Position[]>("/positions").then((r) => r.data),
};
