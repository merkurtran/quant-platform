"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { toast } from "sonner";
import { useBacktestRun } from "@/hooks/use-backtest-run";
import { strategyService } from "@/services/strategies";
import { fieldsToParams, paramsToFields, type StrategyParameterField } from "@/lib/strategy-parameters";
import type { BacktestResultViewModel } from "@/components/panels/backtest-result";
import type { BacktestRunSummary } from "@/types";

interface RunContext {
  runId: number;
  strategyName: string;
  symbol: string;
  startDate: string;
  endDate: string;
  initialCapital: string;
}

export function useStrategyBacktestPanel(
  symbol: string | null,
  onResultChange?: (result: BacktestResultViewModel | null) => void
) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryStrategyId = Number(searchParams.get("strategyId"));
  const queryRunId = Number(searchParams.get("runId"));
  const initialRunId = Number.isInteger(queryRunId) && queryRunId > 0 ? queryRunId : null;
  const [startDate, setStartDate] = useState(dayjs().subtract(1, "year").format("YYYY-MM-DD"));
  const [endDate, setEndDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [capital, setCapital] = useState("1000000");
  const [commissionRate, setCommissionRate] = useState("0.001");
  const [slippageRate, setSlippageRate] = useState("0.0005");
  const [backtestSymbol, setBacktestSymbol] = useState(symbol ?? "");
  const [parameterFields, setParameterFields] = useState<StrategyParameterField[]>([]);
  const [runContext, setRunContext] = useState<RunContext | null>(null);
  const parameterStrategyRef = useRef<number | null>(null);
  const { start, result, isRunning } = useBacktestRun(initialRunId);

  const strategiesQuery = useQuery({ queryKey: ["strategies"], queryFn: strategyService.list });
  const strategyId =
    (Number.isInteger(queryStrategyId) && queryStrategyId > 0
      ? queryStrategyId
      : strategiesQuery.data?.[0]?.id) ?? null;
  const strategyQuery = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId!),
    enabled: strategyId !== null,
  });
  const historyQuery = useQuery({
    queryKey: ["backtest-runs", strategyId],
    queryFn: () => strategyService.listBacktestRuns(strategyId!),
    enabled: strategyId !== null,
  });
  const strategy = strategyQuery.data;

  useEffect(() => {
    if (!strategy || parameterStrategyRef.current === strategy.id) return;
    parameterStrategyRef.current = strategy.id;
    setParameterFields(paramsToFields(strategy.params, strategy.code));
  }, [strategy]);

  const activeRunContext = useMemo<RunContext | null>(() => {
    if (result) {
      return {
        runId: result.run_id,
        strategyName: strategy?.name ?? "策略回测",
        symbol: result.symbols[0] ?? backtestSymbol,
        startDate: result.start_date,
        endDate: result.end_date,
        initialCapital: String(result.initial_capital),
      };
    }
    return runContext;
  }, [backtestSymbol, result, runContext, strategy?.name]);

  useEffect(() => {
    if (!result || !activeRunContext || result.run_id !== activeRunContext.runId) return;
    onResultChange?.({ run: result, ...activeRunContext });
  }, [activeRunContext, onResultChange, result]);

  const selectStrategy = (value: string) => {
    onResultChange?.(null);
    parameterStrategyRef.current = null;
    const params = new URLSearchParams(searchParams);
    params.set("strategyId", value);
    params.delete("runId");
    router.replace(`/market?${params.toString()}`);
  };

  const selectHistory = (run: BacktestRunSummary) => {
    onResultChange?.(null);
    setStartDate(run.start_date);
    setEndDate(run.end_date);
    setCapital(String(run.initial_capital));
    setCommissionRate(String(run.commission_rate));
    setSlippageRate(String(run.slippage_rate));
    setBacktestSymbol(run.symbols[0] ?? "");
    setParameterFields(paramsToFields(run.params_snapshot, strategy?.code));
    const params = new URLSearchParams(searchParams);
    params.set("panel", "backtest");
    params.set("runId", run.run_id.toString());
    params.set("strategyId", run.strategy_id.toString());
    if (run.symbols[0]) params.set("symbol", run.symbols[0]);
    router.replace(`/market?${params.toString()}`);
  };

  const handleStart = async () => {
    if (!strategy || !backtestSymbol) return;
    const commission = Number(commissionRate);
    const slippage = Number(slippageRate);
    if (
      !Number.isFinite(commission) ||
      !Number.isFinite(slippage) ||
      commission < 0 ||
      commission > 0.1 ||
      slippage < 0 ||
      slippage > 0.1
    ) {
      toast.error("手续费率和滑点率需在 0 至 0.1 之间");
      return;
    }
    let runParams: Record<string, unknown>;
    try {
      runParams = fieldsToParams(parameterFields);
    } catch {
      toast.error("策略参数值格式不正确");
      return;
    }
    onResultChange?.(null);
    const runId = await start({
      strategyId: strategy.id,
      startDate,
      endDate,
      initialCapital: capital,
      commissionRate,
      slippageRate,
      symbols: [backtestSymbol],
      params: runParams,
    });
    if (runId === null) return;
    setRunContext({ runId, strategyName: strategy.name, symbol: backtestSymbol, startDate, endDate, initialCapital: capital });
    const params = new URLSearchParams(searchParams);
    params.set("runId", runId.toString());
    router.replace(`/market?${params.toString()}`);
  };

  return {
    strategies: strategiesQuery.data,
    isLoading: strategiesQuery.isLoading,
    strategyId,
    strategy,
    startDate,
    endDate,
    capital,
    commissionRate,
    slippageRate,
    backtestSymbol,
    parameterFields,
    history: historyQuery.data ?? [],
    historyLoading: historyQuery.isLoading,
    activeRunId: result?.run_id ?? initialRunId,
    result,
    isRunning,
    setStartDate,
    setEndDate,
    setCapital,
    setCommissionRate,
    setSlippageRate,
    setBacktestSymbol,
    setParameterFields,
    selectStrategy,
    selectHistory,
    handleStart,
  };
}
