"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus, Trash2 } from "lucide-react";
import { tradingService } from "@/services/trading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
import { formatDate, formatMoney } from "@/lib/format";
import { toast } from "sonner";

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [alias, setAlias] = useState("");
  const [initialCash, setInitialCash] = useState("1000000");
  const [brokerType, setBrokerType] = useState("mock");
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: accounts, isLoading } = useQuery({
    queryKey: ["broker-accounts"],
    queryFn: tradingService.listAccounts,
    refetchInterval: 2_000,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      tradingService.createAccount({
        broker_type: brokerType,
        account_alias: alias,
        initial_cash: initialCash,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broker-accounts"] });
      setOpen(false);
      setAlias("");
      setInitialCash("1000000");
      toast.success("创建成功");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => tradingService.deleteAccount(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broker-accounts"] });
      setDeleteId(null);
      toast.success("已删除");
    },
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">交易 · 券商账户</h1>
        <Button onClick={() => setOpen(true)}>
          <Plus className="h-4 w-4" />
          添加账户
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 2 }).map((_, i) => (
            <TableSkeleton key={i} rows={2} cols={2} />
          ))}
        </div>
      ) : !accounts || accounts.length === 0 ? (
        <EmptyState
          icon={CreditCard}
          title="还没有券商账户"
          description="添加一个模拟券商账户，开始模拟交易"
          action={
            <Button onClick={() => setOpen(true)}>
              <Plus className="h-4 w-4" />
              添加账户
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {accounts.map((a) => (
            <Card key={a.id}>
              <CardContent className="p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold">{a.account_alias}</h3>
                    <p className="mt-0.5 text-sm text-muted-foreground">
                      {a.broker_type}
                    </p>
                  </div>
                  <Badge variant={a.status === "active" ? "success" : "secondary"}>
                    {a.status === "active" ? "活跃" : "未激活"}
                  </Badge>
                </div>
                <p className="mt-3 text-xs text-muted-foreground tabular-nums">
                  创建于 {formatDate(a.created_at)}
                </p>
                <div className="mt-3 flex items-center justify-between border-t border-border/60 pt-3 text-sm">
                  <span className="text-muted-foreground">可用资金</span>
                  <span className="font-semibold tabular-nums">
                    {formatMoney(Number(a.cash_balance))}
                  </span>
                </div>
                <div className="mt-3 flex justify-end">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-danger hover:text-danger"
                    onClick={() => setDeleteId(a.id)}
                  >
                    <Trash2 className="h-4 w-4" /> 删除
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加券商账户</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="initial-cash">初始资金 *</Label>
              <Input
                id="initial-cash"
                inputMode="decimal"
                value={initialCash}
                onChange={(e) => setInitialCash(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="alias">账户别名 *</Label>
              <Input
                id="alias"
                value={alias}
                onChange={(e) => setAlias(e.target.value)}
                placeholder="如：模拟账户1"
              />
            </div>
            <div className="space-y-1.5">
              <Label>券商类型</Label>
              <Select value={brokerType} onValueChange={setBrokerType}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="mock">mock（模拟）</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!alias || !initialCash || createMutation.isPending}
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
            <AlertDialogTitle>确认删除该券商账户？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后无法恢复，该账户下的持仓和未完成订单可能受到影响。
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
