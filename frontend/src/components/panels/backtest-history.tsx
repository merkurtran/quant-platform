import dayjs from "dayjs";
import { CheckCircle2, ChevronRight, Clock3, History, Loader2, XCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { BacktestRunSummary } from "@/types";

interface BacktestHistoryProps {
  runs: BacktestRunSummary[];
  activeRunId: number | null;
  isLoading: boolean;
  onSelect: (run: BacktestRunSummary) => void;
}

export function BacktestHistory({ runs, activeRunId, isLoading, onSelect }: BacktestHistoryProps) {
  return (
    <section className="pt-2">
      <div className="mb-2 flex items-center gap-2 px-1">
        <History className="h-3.5 w-3.5 text-primary" />
        <h4 className="text-xs font-semibold">历史回测</h4>
        {!isLoading && <span className="ml-auto text-[10px] text-muted-foreground">最近 {runs.length} 次</span>}
      </div>

      {isLoading ? (
        <div className="flex h-16 items-center justify-center text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
        </div>
      ) : runs.length === 0 ? (
        <p className="rounded bg-muted/40 px-3 py-4 text-center text-xs text-muted-foreground">暂无历史回测</p>
      ) : (
        <div className="space-y-1">
          {runs.map((run) => (
            <button
              key={run.run_id}
              type="button"
              onClick={() => onSelect(run)}
              className={cn(
                "grid w-full grid-cols-[18px_minmax(0,1fr)_auto_14px] items-center gap-2 rounded px-2 py-2 text-left hover:bg-muted",
                activeRunId === run.run_id && "bg-primary/10"
              )}
            >
              <StatusIcon status={run.status} />
              <span className="min-w-0">
                <span className="block truncate text-[11px] font-medium">{run.symbols.join("、") || "--"}</span>
                <span className="mt-0.5 block text-[10px] tabular-nums text-muted-foreground">
                  {dayjs(run.created_at).format("MM-DD HH:mm")} · {run.start_date.slice(0, 7)} 至 {run.end_date.slice(0, 7)}
                </span>
              </span>
              <span className={cn("text-xs font-semibold tabular-nums", returnTone(run.result?.total_return))}>
                {formatReturn(run.result?.total_return)}
              </span>
              <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
            </button>
          ))}
        </div>
      )}
    </section>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "success") return <CheckCircle2 className="h-3.5 w-3.5 text-success" />;
  if (status === "failed") return <XCircle className="h-3.5 w-3.5 text-danger" />;
  if (status === "queued" || status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />;
  return <Clock3 className="h-3.5 w-3.5 text-muted-foreground" />;
}

function formatReturn(value?: number | null) {
  return value == null ? "--" : `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
}

function returnTone(value?: number | null) {
  if (value == null) return "text-muted-foreground";
  return value >= 0 ? "text-up" : "text-down";
}
