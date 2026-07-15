import api from "@/lib/api";
import type {
  Strategy,
  StrategyDetail,
  BacktestRun,
  BacktestRunResult,
  BacktestRunSummary,
} from "@/types";

export const strategyService = {
  list: () => api.get<Strategy[]>("/strategies").then((r) => r.data),

  get: (id: number) =>
    api.get<StrategyDetail>(`/strategies/${id}`).then((r) => r.data),

  create: (data: {
    name: string;
    description?: string;
    code: string;
    params?: Record<string, unknown>;
  }) => api.post<Strategy>("/strategies", data).then((r) => r.data),

  update: (
    id: number,
    data: {
      name?: string;
      description?: string;
      code?: string;
      params?: Record<string, unknown>;
    }
  ) => api.put<Strategy>(`/strategies/${id}`, data).then((r) => r.data),

  delete: (id: number) => api.delete(`/strategies/${id}`),

  startBacktest: (
    strategyId: number,
    data: {
      start_date: string;
      end_date: string;
      initial_capital: string;
      commission_rate: string;
      slippage_rate: string;
      symbols: string[];
      params?: Record<string, unknown>;
    }
  ) =>
    api
      .post<BacktestRun>(`/strategies/${strategyId}/backtest`, data)
      .then((r) => r.data),

  getBacktestRun: (runId: number) =>
    api
      .get<BacktestRunResult>(`/backtest_runs/${runId}`)
      .then((r) => r.data),

  listBacktestRuns: (strategyId: number, limit = 20) =>
    api
      .get<BacktestRunSummary[]>("/backtest_runs", {
        params: { strategy_id: strategyId, limit },
      })
      .then((r) => r.data),
};
