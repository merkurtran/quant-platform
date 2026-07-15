import Link from "next/link";
import { Code2, Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface BacktestPanelHeaderProps {
  strategyId: number | null;
}

export function BacktestPanelHeader({ strategyId }: BacktestPanelHeaderProps) {
  return (
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
  );
}

export function BacktestEmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 text-center">
      <Code2 className="h-8 w-8 text-muted-foreground" />
      <p className="text-xs text-muted-foreground">暂无可回测策略</p>
      <Button size="sm" asChild>
        <Link href="/strategies/new">新建策略</Link>
      </Button>
    </div>
  );
}

interface BacktestFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}

export function BacktestField({ label, value, onChange, type = "text" }: BacktestFieldProps) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs">{label}</Label>
      <Input className="h-8 text-xs" type={type} value={value} onChange={(event) => onChange(event.target.value)} />
    </div>
  );
}

interface BacktestStatusProps {
  status?: string;
  errorMessage?: string | null;
}

export function BacktestStatus({ status, errorMessage }: BacktestStatusProps) {
  if (status === "failed") {
    return (
      <div className="rounded border border-danger/30 bg-danger/5 p-3 text-xs text-danger">
        {errorMessage ?? "回测失败"}
      </div>
    );
  }
  if (status !== "success") return null;

  return (
    <div className="rounded border border-success/30 bg-success/5 p-3 text-xs text-success">
      回测已完成，结果显示在左侧
    </div>
  );
}
