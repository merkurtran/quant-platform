"use client";

import { useEffect, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { strategyService } from "@/services/strategies";
import { toast } from "sonner";
import type { BacktestRunResult } from "@/types";

interface StartBacktestInput {
  strategyId: number;
  startDate: string;
  endDate: string;
  initialCapital: string;
  commissionRate: string;
  slippageRate: string;
  symbols: string[];
  params?: Record<string, unknown>;
}

export function useBacktestRun(initialRunId?: number | null) {
  const queryClient = useQueryClient();
  const routeRunId = initialRunId ?? null;
  const [runSelection, setRunSelection] = useState({
    routeRunId,
    runId: routeRunId,
  });
  const runId =
    runSelection.routeRunId === routeRunId ? runSelection.runId : routeRunId;
  const [isStarting, setIsStarting] = useState(false);
  const startedRunId = useRef<number | null>(null);

  const { data: result } = useQuery({
    queryKey: ["backtest-run", runId],
    queryFn: () => strategyService.getBacktestRun(runId!),
    enabled: runId !== null,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (!result || startedRunId.current !== result.run_id) return;
    if (result.status === "success") {
      startedRunId.current = null;
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["backtest-runs"] });
      toast.success("回测完成");
    } else if (result.status === "failed") {
      startedRunId.current = null;
      toast.error(`回测失败：${result.error_message ?? "未知错误"}`);
    }
  }, [queryClient, result]);

  const start = async (input: StartBacktestInput) => {
    setIsStarting(true);
    setRunSelection({ routeRunId, runId: null });
    startedRunId.current = null;
    try {
      const run = await strategyService.startBacktest(input.strategyId, {
        start_date: input.startDate,
        end_date: input.endDate,
        initial_capital: input.initialCapital,
        commission_rate: input.commissionRate,
        slippage_rate: input.slippageRate,
        symbols: input.symbols,
        params: input.params,
      });
      startedRunId.current = run.run_id;
      setRunSelection({ routeRunId, runId: run.run_id });
      toast.success("回测已进入队列");
      return run.run_id;
    } catch {
      toast.error("发起回测失败，请检查参数");
      return null;
    } finally {
      setIsStarting(false);
    }
  };

  const isRunning =
    isStarting || result?.status === "queued" || result?.status === "running";

  return { start, result: result as BacktestRunResult | undefined, isRunning };
}
