"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { Code2, Loader2, Pencil, Play } from "lucide-react";
import { strategyService } from "@/services/strategies";
import { useBacktestRun } from "@/hooks/use-backtest-run";
import { BacktestResult } from "@/components/panels/backtest-result";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
}

export function StrategyBacktestPanel({ symbol }: StrategyBacktestPanelProps) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryStrategyId = Number(searchParams.get("strategyId"));
  const [startDate, setStartDate] = useState(
    dayjs().subtract(1, "year").format("YYYY-MM-DD")
  );
  const [endDate, setEndDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [capital, setCapital] = useState("1000000");
  const [backtestSymbol, setBacktestSymbol] = useState(symbol ?? "");
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

  const selectStrategy = (value: string) => {
    const params = new URLSearchParams(searchParams);
    params.set("strategyId", value);
    router.replace(`/market?${params.toString()}`);
  };

  const handleStart = () => {
    if (!strategy || !backtestSymbol) return;
    start({
      strategyId: strategy.id,
      startDate,
      endDate,
      initialCapital: capital,
      symbols: [backtestSymbol],
      params: strategy.params,
    });
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-10 items-center justify-between px-3">
        <h3 className="text-xs font-semibold">策略回测</h3>
        {strategyId && (
          <Button variant="ghost" size="icon" className="h-7 w-7" asChild>
            <Link href={`/strategies/${strategyId}`} title="编辑策略">
              <Pencil className="h-3.5 w-3.5" />
            </Link>
          </Button>
        )}
      </div>

      <div className="flex-1 space-y-4 overflow-y-auto border-t border-border/70 p-3">
        {isLoading ? (
          <div className="space-y-3">
            <div className="h-9 animate-pulse rounded bg-muted" />
            <div className="h-32 animate-pulse rounded bg-muted" />
          </div>
        ) : !strategies?.length ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
            <Code2 className="h-8 w-8 text-muted-foreground" />
            <p className="text-xs text-muted-foreground">暂无可回测策略</p>
            <Button size="sm" asChild>
              <Link href="/strategies/new">新建策略</Link>
            </Button>
          </div>
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
              <Field label="开始日期" type="date" value={startDate} onChange={setStartDate} />
              <Field label="结束日期" type="date" value={endDate} onChange={setEndDate} />
            </div>
            <Field label="回测标的" value={backtestSymbol} onChange={setBacktestSymbol} />
            <Field label="初始资金" value={capital} onChange={setCapital} />

            <Button
              className="w-full"
              size="sm"
              onClick={handleStart}
              disabled={isRunning || !strategy || !backtestSymbol || !startDate || !endDate}
            >
              {isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              {isRunning ? "回测运行中" : "开始回测"}
            </Button>

            {result && <BacktestResult result={result} />}
          </>
        )}
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}

function Field({ label, value, onChange, type = "text" }: FieldProps) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Input className="h-8 text-xs" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}
