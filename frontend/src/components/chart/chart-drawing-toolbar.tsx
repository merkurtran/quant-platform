"use client";

import {
  ArrowUpRight,
  ChartNoAxesColumnIncreasing,
  Eraser,
  Minus,
  MousePointer2,
  Square,
  Trash2,
  TrendingUp,
} from "lucide-react";
import type { CoreDrawingTool } from "@/hooks/use-chart-drawings";
import { cn } from "@/lib/utils";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

interface ChartDrawingToolbarProps {
  activeTool: CoreDrawingTool | null;
  hasSelection: boolean;
  onSelectTool: (tool: CoreDrawingTool | null) => void;
  onDeleteSelected: () => void;
  onClearAll: () => void;
}

const TOOLS = [
  { type: null, label: "选择", icon: MousePointer2 },
  { type: "trend-line", label: "趋势线", icon: TrendingUp },
  { type: "horizontal-line", label: "水平线", icon: Minus },
  { type: "fib-retracement", label: "斐波那契回撤", icon: ChartNoAxesColumnIncreasing },
  { type: "rectangle", label: "矩形", icon: Square },
  { type: "arrow", label: "箭头", icon: ArrowUpRight },
] satisfies Array<{ type: CoreDrawingTool | null; label: string; icon: typeof MousePointer2 }>;

export function ChartDrawingToolbar(props: ChartDrawingToolbarProps) {
  return (
    <aside className="flex h-full w-10 flex-col items-center gap-1 bg-card py-2">
      {TOOLS.map(({ type, label, icon: Icon }) => (
        <ToolButton
          key={label}
          label={label}
          active={props.activeTool === type}
          onClick={() => props.onSelectTool(type)}
        >
          <Icon className="h-4 w-4" strokeWidth={1.6} />
        </ToolButton>
      ))}

      <div className="my-1 h-px w-5 bg-border" />
      <ToolButton label="删除选中图形" disabled={!props.hasSelection} onClick={props.onDeleteSelected}>
        <Eraser className="h-4 w-4" strokeWidth={1.6} />
      </ToolButton>

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <div>
            <ToolButton label="清空全部图形">
              <Trash2 className="h-4 w-4" strokeWidth={1.6} />
            </ToolButton>
          </div>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>清空全部画图？</AlertDialogTitle>
            <AlertDialogDescription>当前股票上的趋势线和标注将全部删除。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={props.onClearAll}>确认清空</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </aside>
  );
}

interface ToolButtonProps {
  label: string;
  active?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: React.ReactNode;
}

function ToolButton({ label, active, disabled, onClick, children }: ToolButtonProps) {
  return (
    <button
      type="button"
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "group relative flex h-8 w-8 items-center justify-center rounded text-muted-foreground transition-colors",
        "hover:bg-muted hover:text-foreground disabled:pointer-events-none disabled:opacity-35",
        active && "bg-primary/10 text-primary"
      )}
    >
      {children}
      <span className="pointer-events-none absolute left-full z-50 ml-2 whitespace-nowrap rounded bg-popover px-2 py-1 text-xs text-foreground opacity-0 shadow-md transition-opacity group-hover:opacity-100">
        {label}
      </span>
    </button>
  );
}
