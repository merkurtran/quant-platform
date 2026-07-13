"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { CreditCard, Plus } from "lucide-react";
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
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
import { formatDate } from "@/lib/format";
import { toast } from "sonner";

export default function AccountsPage() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [alias, setAlias] = useState("");
  const [brokerType, setBrokerType] = useState("mock");

  const { data: accounts, isLoading } = useQuery({
    queryKey: ["broker-accounts"],
    queryFn: tradingService.listAccounts,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      tradingService.createAccount({ broker_type: brokerType, account_alias: alias }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["broker-accounts"] });
      setOpen(false);
      setAlias("");
      toast.success("创建成功");
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
              <Label htmlFor="alias">账户别名 *</Label>
              <Input
                id="alias"
                value={alias}
                onChange={(e) => setAlias(e.target.value)}
                placeholder="如：模拟账户1"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="broker">券商类型</Label>
              <Input
                id="broker"
                value={brokerType}
                onChange={(e) => setBrokerType(e.target.value)}
                placeholder="mock"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={() => createMutation.mutate()}
              disabled={!alias || createMutation.isPending}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
