import { formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { BacktestRunResult } from "@/types";

interface BacktestResultProps {
  result: BacktestRunResult;
}

export function BacktestResult({ result }: BacktestResultProps) {
  if (result.status === "failed") {
    return (
      <p className="text-xs text-danger">
        {result.error_message ?? "回测失败"}
      </p>
    );
  }
  if (!result.result) return null;

  return (
    <div className="grid grid-cols-2 gap-px overflow-hidden rounded border border-border bg-border">
      <Metric label="总收益率" value={formatPercent(result.result.total_return)} raw={result.result.total_return} />
      <Metric label="年化收益" value={formatPercent(result.result.annual_return)} raw={result.result.annual_return} />
      <Metric label="最大回撤" value={formatPercent(result.result.max_drawdown)} raw={result.result.max_drawdown} />
      <Metric label="夏普比率" value={result.result.sharpe_ratio?.toFixed(4) ?? "--"} />
      <Metric label="胜率" value={formatPercent(result.result.win_rate)} />
      <Metric label="交易次数" value={result.result.trade_count?.toString() ?? "--"} />
    </div>
  );
}

interface MetricProps {
  label: string;
  value: string;
  raw?: number | null;
}

function Metric({ label, value, raw }: MetricProps) {
  return (
    <div className="bg-card p-2.5">
      <p className="text-[10px] text-muted-foreground">{label}</p>
      <p className={cn("mt-1 text-sm font-semibold tabular-nums", raw != null && raw > 0 && "text-up", raw != null && raw < 0 && "text-down")}>{value}</p>
    </div>
  );
}
