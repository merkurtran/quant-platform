"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { Loader2, Play } from "lucide-react";
import { strategyService } from "@/services/strategies";
import { useBacktestRun } from "@/hooks/use-backtest-run";
import type { BacktestResultViewModel } from "@/components/panels/backtest-result";
import {
  BacktestEmptyState,
  BacktestField,
  BacktestPanelHeader,
  BacktestStatus,
} from "@/components/panels/strategy-backtest-states";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface StrategyBacktestPanelProps {
  symbol: string | null;
  onResultChange?: (result: BacktestResultViewModel | null) => void;
}

interface RunContext {
  runId: number;
  strategyName: string;
  symbol: string;
  startDate: string;
  endDate: string;
  initialCapital: string;
}

export function StrategyBacktestPanel({ symbol, onResultChange }: StrategyBacktestPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryStrategyId = Number(searchParams.get("strategyId"));
  const [startDate, setStartDate] = useState(
    dayjs().subtract(1, "year").format("YYYY-MM-DD")
  );
  const [endDate, setEndDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [capital, setCapital] = useState("1000000");
  const [backtestSymbol, setBacktestSymbol] = useState(symbol ?? "");
  const [runContext, setRunContext] = useState<RunContext | null>(null);
  const { start, result, isRunning } = useBacktestRun();

  const { data: strategies, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: strategyService.list,
  });
  const strategyId =
    (Number.isInteger(queryStrategyId) && queryStrategyId > 0
      ? queryStrategyId
      : strategies?.[0]?.id) ?? null;
  const { data: strategy } = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId!),
    enabled: strategyId !== null,
  });

  useEffect(() => {
    if (!result || !runContext || result.run_id !== runContext.runId) return;
    onResultChange?.({
      run: result,
      strategyName: runContext.strategyName,
      symbol: runContext.symbol,
      startDate: runContext.startDate,
      endDate: runContext.endDate,
      initialCapital: runContext.initialCapital,
    });
  }, [onResultChange, result, runContext]);

  const selectStrategy = (value: string) => {
    onResultChange?.(null);
    const params = new URLSearchParams(searchParams);
    params.set("strategyId", value);
    router.replace(`/market?${params.toString()}`);
  };

  const handleStart = async () => {
    if (!strategy || !backtestSymbol) return;
    onResultChange?.(null);
    const runId = await start({
      strategyId: strategy.id,
      startDate,
      endDate,
      initialCapital: capital,
      symbols: [backtestSymbol],
      params: strategy.params,
    });
    if (runId !== null) {
      setRunContext({
        runId,
        strategyName: strategy.name,
        symbol: backtestSymbol,
        startDate,
        endDate,
        initialCapital: capital,
      });
    }
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <BacktestPanelHeader strategyId={strategyId} />

      <div className="flex-1 space-y-4 overflow-y-auto border-t border-border/70 p-3">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-9 animate-pulse rounded bg-muted" />
            <div className="h-32 animate-pulse rounded bg-muted" />
          </div>
        ) : !strategies?.length ? (
          <BacktestEmptyState />
        ) : (
          <>
            <div className="space-y-1.5">
              <Label className="text-xs">策略</Label>
              <Select value={strategyId?.toString()} onValueChange={selectStrategy}>
                <SelectTrigger className="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {strategies.map((item) => (
                    <SelectItem key={item.id} value={item.id.toString()}>
                      {item.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <BacktestField label="开始日期" type="date" value={startDate} onChange={setStartDate} />
              <BacktestField label="结束日期" type="date" value={endDate} onChange={setEndDate} />
            </div>
            <BacktestField label="回测标的" value={backtestSymbol} onChange={setBacktestSymbol} />
            <BacktestField label="初始资金" value={capital} onChange={setCapital} />

            <Button
              className="w-full"
              size="sm"
              onClick={handleStart}
              disabled={isRunning || !strategy || !backtestSymbol || !startDate || !endDate}
            >
              {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {isRunning ? "回测运行中" : "开始回测"}
            </Button>

            <BacktestStatus status={result?.status} errorMessage={result?.error_message} />
          </>
        )}
      </div>
    </div>
  );
}
