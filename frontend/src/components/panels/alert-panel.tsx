"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Bell, Plus, Pause, Play, Trash2 } from "lucide-react";
import { alertService } from "@/services/alerts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { ALERT_RULE_TYPE_LABELS } from "@/constants";
import { formatPrice, formatRelative } from "@/lib/format";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { AlertRuleType } from "@/types";

export function AlertPanel() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const [symbol, setSymbol] = useState("");
  const [ruleType, setRuleType] = useState<AlertRuleType>("price_above");
  const [value, setValue] = useState("");

  const { data: rules, isLoading } = useQuery({
    queryKey: ["alerts", statusFilter],
    queryFn: () =>
      alertService.list(
        statusFilter === "all" ? {} : { rule_status: statusFilter }
      ),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const condition: Record<string, unknown> = { rule_type: ruleType };
      if (ruleType === "price_above" || ruleType === "price_below") {
        condition.value = value;
      } else if (ruleType === "pct_change") {
        condition.operator = "gt";
        condition.value = value;
        condition.baseline = "previous_close";
      }
      return alertService.create({
        symbol,
        condition: condition as never,
        notify_channels: ["inapp"],
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setCreateOpen(false);
      setSymbol("");
      setValue("");
      toast.success("创建成功");
    },
  });

  const toggleStatusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: "active" | "paused" }) =>
      alertService.update(id, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => alertService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setDeleteId(null);
      toast.success("已删除");
    },
  });

  return (
    <div className="flex h-full flex-col">
      {/* 顶栏 */}
      <div className="flex h-10 items-center justify-between px-3">
        <h3 className="text-xs font-semibold">告警规则</h3>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => setCreateOpen(true)}
        >
          <Plus className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* 状态筛选 — 用 muted 背景色块分隔 */}
      <div className="flex gap-1 bg-muted/30 px-2 py-1.5">
        {["all", "active", "paused"].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "rounded-full px-3 py-0.5 text-xs font-medium transition-colors",
              statusFilter === s
                ? "bg-card text-foreground shadow-sm"
                : "text-muted-foreground hover:text-foreground"
            )}
          >
            {s === "all" ? "全部" : s === "active" ? "运行中" : "已暂停"}
          </button>
        ))}
      </div>

      {/* 列表 */}
      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="p-3 text-center text-xs text-muted-foreground">
            加载中...
          </div>
        ) : !rules || rules.length === 0 ? (
          <div className="flex flex-col items-center gap-2 px-3 py-8 text-center">
            <Bell className="h-8 w-8 text-muted-foreground/50" />
            <p className="text-xs text-muted-foreground">暂无告警规则</p>
          </div>
        ) : (
          <ul>
            {rules.map((r, i) => (
              <li
                key={r.id}
                className={cn(
                  "px-3 py-2 transition-colors hover:bg-accent",
                  i % 2 === 1 && "bg-muted/20"
                )}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-1.5">
                  <span className="text-xs font-medium tabular-nums">
                    {r.symbol}
                  </span>
                  <Badge variant="outline" className="h-4 text-[10px]">
                    {ALERT_RULE_TYPE_LABELS[r.rule_type] ?? r.rule_type}
                  </Badge>
                </div>
                <Badge
                  variant={r.status === "active" ? "success" : "secondary"}
                  className="h-4 text-[10px]"
                >
                  {r.status === "active" ? "运行" : "暂停"}
                </Badge>
              </div>

              {r.condition.value && (
                <p className="mt-0.5 text-[10px] text-muted-foreground tabular-nums">
                  阈值 {formatPrice(r.condition.value)}
                </p>
              )}

              {r.last_triggered_at && (
                <p className="mt-0.5 text-[10px] text-muted-foreground">
                  上次触发 {formatRelative(r.last_triggered_at)}
                </p>
              )}

              <div className="mt-1.5 flex items-center gap-1">
                <button
                  onClick={() =>
                    toggleStatusMutation.mutate({
                      id: r.id,
                      status: r.status === "active" ? "paused" : "active",
                    })
                  }
                  className="rounded p-1 text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
                >
                  {r.status === "active" ? (
                    <Pause className="h-3 w-3" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                </button>
                <button
                  onClick={() => setDeleteId(r.id)}
                  className="rounded p-1 text-muted-foreground transition-colors hover:text-danger"
                >
                  <Trash2 className="h-3 w-3" />
                </button>
              </div>
            </li>
            ))}
          </ul>
        )}
      </div>

      {/* 创建规则 Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建告警规则</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>股票代码 *</Label>
                <Input
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value)}
                  placeholder="600519.SH"
                />
              </div>
              <div className="space-y-1.5">
                <Label>规则类型 *</Label>
                <Select
                  value={ruleType}
                  onValueChange={(v) => setRuleType(v as AlertRuleType)}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="price_above">价格上穿</SelectItem>
                    <SelectItem value="price_below">价格下穿</SelectItem>
                    <SelectItem value="pct_change">涨跌幅</SelectItem>
                    <SelectItem value="volume_spike">量异动</SelectItem>
                    <SelectItem value="indicator">指标触发</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>
                {ruleType === "pct_change"
                  ? "涨跌幅阈值（%）"
                  : ruleType === "volume_spike"
                  ? "成交量倍数（倍）"
                  : "价格阈值"}{" "}
                *
              </Label>
              <Input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={ruleType === "pct_change" ? "5.0" : "1700"}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!symbol || !value || createMutation.isPending}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AlertDialog
        open={deleteId !== null}
        onOpenChange={(open) => !open && setDeleteId(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除该告警规则？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复，相关触发日志也会被清除。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
            >
              确认删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
