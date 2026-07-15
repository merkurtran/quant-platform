import { Activity, CheckCircle2 } from "lucide-react";
import { EquityCurveChart } from "@/components/chart/equity-curve-chart";
import { formatMoney, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BacktestRunResult } from "@/types";

export interface BacktestResultViewModel {
  run: BacktestRunResult;
  strategyName: string;
  symbol: string;
  startDate: string;
  endDate: string;
  initialCapital: string;
}

interface BacktestResultProps {
  backtest: BacktestResultViewModel;
}

export function BacktestResult({ backtest }: BacktestResultProps) {
  const result = backtest.run.result;
  if (!result) return null;
  const drawdown = result.max_drawdown == null ? null : -Math.abs(result.max_drawdown);

  const metrics = [
    { label: "总收益率", value: formatReturn(result.total_return), raw: result.total_return },
    { label: "年化收益率", value: formatReturn(result.annual_return), raw: result.annual_return },
    { label: "最大回撤", value: formatPercent(drawdown), raw: drawdown },
    { label: "夏普比率", value: result.sharpe_ratio?.toFixed(2) ?? "--", raw: result.sharpe_ratio },
    { label: "胜率", value: formatPercent(result.win_rate), raw: result.win_rate },
    { label: "交易次数", value: result.trade_count?.toLocaleString("zh-CN") ?? "--" },
  ];

  return (
    <div className="h-full overflow-y-auto bg-background p-4 lg:p-5">
      <div className="flex h-full min-h-[720px] w-full flex-col gap-4">
        <header className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Activity className="h-4 w-4 text-primary" />
              <h2 className="text-base font-semibold">回测结果</h2>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              {backtest.strategyName} · {backtest.symbol} · {backtest.startDate} 至 {backtest.endDate} · 初始资金 ¥{formatMoney(backtest.initialCapital)}
            </p>
            <p className="mt-1 text-[11px] tabular-nums text-muted-foreground">
              手续费率 {formatRate(backtest.run.commission_rate)} · 滑点率 {formatRate(backtest.run.slippage_rate)}
            </p>
          </div>
          <span className="inline-flex h-6 items-center gap-1.5 rounded bg-success/10 px-2 text-xs font-medium text-success">
            <CheckCircle2 className="h-3.5 w-3.5" />
            已完成 · #{backtest.run.run_id}
          </span>
        </header>

        <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
          {metrics.map((metric) => (
            <Metric key={metric.label} {...metric} />
          ))}
        </div>

        <section className="flex min-h-80 flex-1 flex-col overflow-hidden rounded-md border bg-card">
          <div className="flex h-11 items-center justify-between border-b px-4">
            <h3 className="text-sm font-semibold">权益曲线</h3>
            <span className="text-xs text-muted-foreground">组合净值变化</span>
          </div>
          <div className="min-h-0 flex-1">
            {result.equity_curve?.length ? (
              <EquityCurveChart data={result.equity_curve} />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                本次回测未返回权益曲线
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

function formatReturn(value: number | null) {
  return formatPercent(value == null ? null : value * 100);
}

function formatRate(value: string) {
  return `${(Number(value) * 100).toFixed(3)}%`;
}

interface MetricProps {
  label: string;
  value: string;
  raw?: number | null;
}

function Metric({ label, value, raw }: MetricProps) {
  return (
    <div className="min-h-28 rounded-md border bg-card p-4">
      <p className="text-xs font-medium uppercase text-muted-foreground">{label}</p>
      <p className={cn("mt-3 text-2xl font-semibold tabular-nums", raw != null && raw > 0 && "text-success", raw != null && raw < 0 && "text-danger")}>{value}</p>
    </div>
  );
}
