"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeftRight, Plus, Ban } from "lucide-react";
import { tradingService } from "@/services/trading";
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
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
import { ORDER_STATUS_LABELS } from "@/constants";
import { formatPrice, formatVolume, formatDateTime } from "@/lib/format";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "success" | "warning" | "danger"> = {
  pending: "warning",
  submitted: "default",
  partial_filled: "warning",
  filled: "success",
  cancelled: "secondary",
  rejected: "danger",
};

export default function OrdersPage() {
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [cancelId, setCancelId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // 表单
  const [accountId, setAccountId] = useState("");
  const [symbol, setSymbol] = useState("");
  const [side, setSide] = useState("buy");
  const [orderType, setOrderType] = useState("limit");
  const [price, setPrice] = useState("");
  const [volume, setVolume] = useState("");

  const { data: accounts } = useQuery({
    queryKey: ["broker-accounts"],
    queryFn: tradingService.listAccounts,
  });

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders", statusFilter],
    queryFn: () =>
      tradingService.listOrders(
        statusFilter === "all" ? {} : { status: statusFilter }
      ),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      tradingService.createOrder({
        broker_account_id: parseInt(accountId),
        symbol,
        side: side as "buy" | "sell",
        order_type: orderType as "limit" | "market",
        price: orderType === "limit" ? price : undefined,
        volume,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      setCreateOpen(false);
      setSymbol("");
      setPrice("");
      setVolume("");
      toast.success("下单成功");
    },
  });

  const cancelMutation = useMutation({
    mutationFn: (id: number) => tradingService.cancelOrder(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      setCancelId(null);
      toast.success("撤单成功");
    },
  });

  const canCancel = (status: string) =>
    ["pending", "submitted", "partial_filled"].includes(status);

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">交易 · 订单</h1>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          下单
        </Button>
      </div>

      {/* 状态筛选 */}
      <div className="flex gap-2">
        {["all", "pending", "submitted", "partial_filled", "filled", "cancelled"].map(
          (s) => (
            <Button
              key={s}
              variant={statusFilter === s ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(s)}
            >
              {s === "all" ? "全部" : ORDER_STATUS_LABELS[s] ?? s}
            </Button>
          )
        )}
      </div>

      {/* 订单表格 */}
      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={6} cols={7} />
            </div>
          ) : !orders || orders.length === 0 ? (
            <EmptyState
              icon={ArrowLeftRight}
              title="暂无订单"
              description="点击下单按钮创建你的第一笔交易"
              action={
                <Button onClick={() => setCreateOpen(true)}>
                  <Plus className="h-4 w-4" />
                  下单
                </Button>
              }
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>时间</TableHead>
                  <TableHead>代码</TableHead>
                  <TableHead>方向</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead className="text-right">价格</TableHead>
                  <TableHead className="text-right">委托量</TableHead>
                  <TableHead className="text-right">已成交</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {orders.map((o) => (
                  <TableRow key={o.id}>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">
                      {formatDateTime(o.created_at)}
                    </TableCell>
                    <TableCell className="font-medium tabular-nums">{o.symbol}</TableCell>
                    <TableCell>
                      <span className={o.side === "buy" ? "text-up" : "text-down"}>
                        {o.side === "buy" ? "买入" : "卖出"}
                      </span>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {o.order_type === "limit" ? "限价" : "市价"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {o.price ? formatPrice(o.price) : "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatVolume(o.volume)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatVolume(o.filled_volume)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={STATUS_VARIANT[o.status] ?? "secondary"}>
                        {ORDER_STATUS_LABELS[o.status] ?? o.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {o.origin === "manual" ? "手动" : o.origin === "strategy" ? "策略" : "AI"}
                    </TableCell>
                    <TableCell>
                      {canCancel(o.status) && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => setCancelId(o.id)}
                        >
                          <Ban className="h-4 w-4 text-danger" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* 下单 Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>下单</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label>券商账户 *</Label>
              <Select value={accountId} onValueChange={setAccountId}>
                <SelectTrigger>
                  <SelectValue placeholder="选择账户" />
                </SelectTrigger>
                <SelectContent>
                  {accounts?.map((a) => (
                    <SelectItem key={a.id} value={a.id.toString()}>
                      {a.account_alias}（{a.broker_type}）
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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
                <Label>方向 *</Label>
                <Select value={side} onValueChange={setSide}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="buy">买入</SelectItem>
                    <SelectItem value="sell">卖出</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>订单类型 *</Label>
                <Select value={orderType} onValueChange={setOrderType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="limit">限价</SelectItem>
                    <SelectItem value="market">市价</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>委托量（股）*</Label>
                <Input
                  type="number"
                  value={volume}
                  onChange={(e) => setVolume(e.target.value)}
                  placeholder="100"
                />
              </div>
            </div>
            {orderType === "limit" && (
              <div className="space-y-1.5">
                <Label>限价价格 *</Label>
                <Input
                  type="number"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="1689.50"
                />
              </div>
            )}
          </div>
          <DialogFooter>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={
                createMutation.isPending ||
                !accountId ||
                !symbol ||
                !volume ||
                (orderType === "limit" && !price)
              }
            >
              确认下单
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 撤单确认 */}
      <AlertDialog open={cancelId !== null} onOpenChange={() => setCancelId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认撤单？</AlertDialogTitle>
            <AlertDialogDescription>
              撤单后订单将无法恢复，已成交部分不受影响。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => cancelId && cancelMutation.mutate(cancelId)}
              disabled={cancelMutation.isPending}
            >
              确认撤单
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
