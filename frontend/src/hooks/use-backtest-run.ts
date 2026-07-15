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
  symbols: string[];
  params?: Record<string, unknown>;
}

export function useBacktestRun() {
  const queryClient = useQueryClient();
  const [runId, setRunId] = useState<number | null>(null);
  const [isStarting, setIsStarting] = useState(false);
  const notifiedRunId = useRef<number | null>(null);

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
    if (!result || notifiedRunId.current === result.run_id) return;
    if (result.status === "success") {
      notifiedRunId.current = result.run_id;
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      toast.success("回测完成");
    } else if (result.status === "failed") {
      notifiedRunId.current = result.run_id;
      toast.error(`回测失败：${result.error_message ?? "未知错误"}`);
    }
  }, [queryClient, result]);

  const start = async (input: StartBacktestInput) => {
    setIsStarting(true);
    setRunId(null);
    notifiedRunId.current = null;
    try {
      const run = await strategyService.startBacktest(input.strategyId, {
        start_date: input.startDate,
        end_date: input.endDate,
        initial_capital: input.initialCapital,
        symbols: input.symbols,
        params: input.params,
      });
      setRunId(run.run_id);
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
