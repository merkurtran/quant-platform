import Link from "next/link";
import { Clock3, MoreHorizontal, Pencil, Play, Trash2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { STRATEGY_STATUS_LABELS } from "@/constants";
import { formatRelative } from "@/lib/format";
import type { Strategy } from "@/types";

const STATUS_VARIANT: Record<
  string,
  "default" | "secondary" | "success" | "warning"
> = {
  draft: "secondary",
  backtested: "default",
  paper_running: "success",
  archived: "warning",
};

interface StrategyCardProps {
  strategy: Strategy;
  onDelete: (id: number) => void;
}

export function StrategyCard({ strategy, onDelete }: StrategyCardProps) {
  return (
    <article className="flex min-h-52 flex-col rounded-lg bg-card p-5 transition-shadow hover:shadow-sm">
      <div className="flex items-start gap-3">
        <Link href={`/strategies/${strategy.id}`} className="min-w-0 flex-1">
          <h2 className="truncate text-base font-semibold hover:text-primary">
            {strategy.name}
          </h2>
        </Link>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-8 w-8" title="更多操作">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem asChild>
              <Link href={`/strategies/${strategy.id}`}>
                <Pencil className="mr-2 h-4 w-4" />
                编辑策略
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              className="text-danger focus:text-danger"
              onSelect={() => onDelete(strategy.id)}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              删除策略
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      <p className="mt-2 line-clamp-3 min-h-16 text-sm leading-5 text-muted-foreground">
        {strategy.description ?? "暂无策略描述"}
      </p>

      <div className="mt-4 flex items-center gap-2">
        <Badge variant={STATUS_VARIANT[strategy.status] ?? "secondary"}>
          {STRATEGY_STATUS_LABELS[strategy.status] ?? strategy.status}
        </Badge>
        <span className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock3 className="h-3 w-3" />
          {formatRelative(strategy.updated_at)}
        </span>
      </div>

      <div className="mt-auto flex gap-2 pt-4">
        <Button variant="outline" size="sm" asChild>
          <Link href={`/strategies/${strategy.id}`}>
            <Pencil className="h-3.5 w-3.5" />
            编辑
          </Link>
        </Button>
        <Button variant="secondary" size="sm" className="flex-1 text-primary" asChild>
          <Link href={`/market?panel=backtest&strategyId=${strategy.id}`}>
            <Play className="h-3.5 w-3.5" />
            回测
          </Link>
        </Button>
      </div>
    </article>
  );
}
