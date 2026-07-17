"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Bell, Plus, Pause, Play, ScrollText, Trash2 } from "lucide-react";
import { alertService } from "@/services/alerts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
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
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
import {
  ALERT_RULE_TYPE_LABELS,
  NOTIFY_CHANNEL_LABELS,
} from "@/constants";
import { formatPrice, formatRelative } from "@/lib/format";
import { toast } from "sonner";
import type { AlertRuleType } from "@/types";

export default function AlertsPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");

  // 表单
  const [symbol, setSymbol] = useState("");
  const [ruleType, setRuleType] = useState<AlertRuleType>("price_above");
  const [value, setValue] = useState("");
  const [cooldown, setCooldown] = useState("");
  const [rearm, setRearm] = useState("");
  const [indicatorName, setIndicatorName] = useState("rsi");
  const [deleteId, setDeleteId] = useState<number | null>(null);

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
      } else if (ruleType === "volume_spike") {
        condition.operator = "gt";
        condition.value = value;
        condition.baseline = "previous_close";
      } else if (ruleType === "indicator") {
        condition.params = {
          indicator: indicatorName,
          operator: "gt",
          value: parseFloat(value),
        };
      }
      return alertService.create({
        symbol,
        condition: condition as never,
        notify_channels: ["inapp"],
        dedup_cooldown_minutes: cooldown ? parseInt(cooldown) : undefined,
        dedup_rearm_pct: rearm || undefined,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alerts"] });
      setCreateOpen(false);
      setSymbol("");
      setValue("");
      setCooldown("");
      setRearm("");
      setIndicatorName("rsi");
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
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">告警</h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          新建规则
        </Button>
      </div>

      <div className="flex gap-2">
        {["all", "active", "paused"].map((s) => (
          <Button
            key={s}
            variant={statusFilter === s ? "default" : "outline"}
            size="sm"
            onClick={() => setStatusFilter(s)}
          >
            {s === "all" ? "全部" : s === "active" ? "运行中" : "已暂停"}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <TableSkeleton key={i} rows={2} cols={2} />
          ))}
        </div>
      ) : !rules || rules.length === 0 ? (
        <EmptyState
          icon={Bell}
          title="还没有告警规则"
          description="创建价格或涨跌幅告警，实时接收推送通知"
          action={
            <Button onClick={() => setCreateOpen(true)}>
              <Plus className="h-4 w-4" />
              新建规则
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {rules.map((r) => (
            <Card key={r.id}>
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-medium tabular-nums">{r.symbol}</span>
                      <Badge variant="outline">
                        {ALERT_RULE_TYPE_LABELS[r.rule_type] ?? r.rule_type}
                      </Badge>
                    </div>
                    <p className="mt-1 text-sm text-muted-foreground">
                      {r.condition.value
                        ? `阈值 ${formatPrice(r.condition.value)}`
                        : "—"}
                    </p>
                  </div>
                  <Badge
                    variant={r.status === "active" ? "success" : "secondary"}
                  >
                    {r.status === "active" ? "运行中" : "已暂停"}
                  </Badge>
                </div>

                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span>
                    通知:{" "}
                    {r.notify_channels
                      .map((c) => NOTIFY_CHANNEL_LABELS[c] ?? c)
                      .join(", ")}
                  </span>
                  <span>冷却: {r.dedup_cooldown_minutes ?? 30}分钟</span>
                  <span>回落: {r.dedup_rearm_pct ?? "2.0"}%</span>
                </div>

                {r.last_triggered_at && (
                  <p className="mt-2 text-xs text-muted-foreground">
                    上次触发: {formatRelative(r.last_triggered_at)}（
                    {formatPrice(r.last_triggered_price)}）
                  </p>
                )}

                <div className="mt-4 flex items-center gap-2">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() =>
                      toggleStatusMutation.mutate({
                        id: r.id,
                        status: r.status === "active" ? "paused" : "active",
                      })
                    }
                  >
                    {r.status === "active" ? (
                      <>
                        <Pause className="h-4 w-4" /> 暂停
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4" /> 启用
                      </>
                    )}
                  </Button>
                  <Button variant="ghost" size="sm" asChild>
                    <Link href={`/alerts/${r.id}/logs`}>
                      <ScrollText className="h-4 w-4" /> 日志
                    </Link>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="ml-auto text-danger hover:text-danger"
                    onClick={() => setDeleteId(r.id)}
                  >
                    <Trash2 className="h-4 w-4" /> 删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

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
            {ruleType === "indicator" && (
              <div className="space-y-1.5">
                <Label>指标名称 *</Label>
                <Input
                  value={indicatorName}
                  onChange={(e) => setIndicatorName(e.target.value)}
                  placeholder="rsi / macd / kdj"
                />
              </div>
            )}
            <div className="space-y-1.5">
              <Label>
                {ruleType === "pct_change"
                  ? "涨跌幅阈值（%）"
                  : ruleType === "volume_spike"
                  ? "成交量倍数（倍）"
                  : ruleType === "indicator"
                  ? "指标阈值"
                  : "价格阈值"}{" "}
                *
              </Label>
              <Input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={
                  ruleType === "pct_change"
                    ? "5.0"
                    : ruleType === "volume_spike"
                    ? "2.0"
                    : ruleType === "indicator"
                    ? "70"
                    : "1700"
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>冷却窗口（分钟）</Label>
                <Input
                  type="number"
                  value={cooldown}
                  onChange={(e) => setCooldown(e.target.value)}
                  placeholder="30"
                />
              </div>
              <div className="space-y-1.5">
                <Label>回落重置（%）</Label>
                <Input
                  type="number"
                  value={rearm}
                  onChange={(e) => setRearm(e.target.value)}
                  placeholder="2.0"
                />
              </div>
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
