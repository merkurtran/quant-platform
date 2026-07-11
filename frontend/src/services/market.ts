import api from "@/lib/api";
import type { KlineListResponse, Watchlist, WatchlistItem } from "@/types";

export const marketService = {
  getKlines: (params: {
    symbol: string;
    period?: string;
    limit?: number;
    adjust?: string;
    start?: string;
    end?: string;
  }) => api.get<KlineListResponse>("/market/klines", { params }).then((r) => r.data),

  getWatchlists: () =>
    api.get<Watchlist[]>("/market/watchlists").then((r) => r.data),

  createWatchlist: (name: string) =>
    api.post<Watchlist>("/market/watchlists", { name }).then((r) => r.data),

  addWatchlistItem: (
    watchlistId: number,
    data: { symbol: string; name?: string }
  ) =>
    api
      .post<WatchlistItem>(`/market/watchlists/${watchlistId}/items`, data)
      .then((r) => r.data),

  removeWatchlistItem: (watchlistId: number, symbol: string) =>
    api
      .delete(`/market/watchlists/${watchlistId}/items/${symbol}`)
      .then((r) => r.data),
};
