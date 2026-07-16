"use client";

import Link from "next/link";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CreditCard, Wallet } from "lucide-react";
import { tradingService } from "@/services/trading";
import { OrderTicket } from "@/components/panels/order-ticket";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
import { ORDER_STATUS_LABELS } from "@/constants";
import { formatPrice, formatVolume } from "@/lib/format";
import { toast } from "sonner";

interface TradingPanelProps {
  symbol: string | null;
}

const CANCELLABLE_STATUSES = ["pending", "submitted", "partial_filled"];

export function TradingPanel({ symbol }: TradingPanelProps) {
  const queryClient = useQueryClient();
  const [cancelId, setCancelId] = useState<number | null>(null);
  const { data: accounts = [], isLoading: accountsLoading } = useQuery({
    queryKey: ["broker-accounts"],
    queryFn: tradingService.listAccounts,
  });
  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => tradingService.listOrders({ page: 1, page_size: 30 }),
    refetchInterval: 2_000,
  });
  const { data: positions = [], isLoading: positionsLoading } = useQuery({
    queryKey: ["positions"],
    queryFn: tradingService.listPositions,
    refetchInterval: 2_000,
  });

  const cancelMutation = useMutation({
    mutationFn: (orderId: number) => tradingService.cancelOrder(orderId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      setCancelId(null);
      toast.success("撤单成功");
    },
  });

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex h-10 items-center justify-between px-3">
        <h3 className="text-xs font-semibold">交易</h3>
        <Button variant="ghost" size="icon" className="h-7 w-7" asChild>
          <Link href="/trading/accounts" title="券商账户"><CreditCard className="h-3.5 w-3.5" /></Link>
        </Button>
      </div>

      <Tabs defaultValue="ticket" className="flex min-h-0 flex-1 flex-col border-t border-border/70">
        <TabsList className="mx-3 mt-2 grid h-8 grid-cols-3">
          <TabsTrigger value="ticket" className="text-xs">下单</TabsTrigger>
          <TabsTrigger value="orders" className="text-xs">订单</TabsTrigger>
          <TabsTrigger value="positions" className="text-xs">持仓</TabsTrigger>
        </TabsList>

        <TabsContent value="ticket" className="mt-0 flex-1 overflow-y-auto">
          {accountsLoading ? (
            <PanelLoading />
          ) : accounts.length ? (
            <OrderTicket accounts={accounts} symbol={symbol} />
          ) : (
            <PanelEmpty icon={<CreditCard className="h-7 w-7" />} text="请先添加券商账户" href="/trading/accounts" action="添加账户" />
          )}
        </TabsContent>

        <TabsContent value="orders" className="mt-2 flex-1 overflow-y-auto px-2 pb-2">
          {ordersLoading ? <PanelLoading /> : orders.length ? orders.map((order) => (
            <div key={order.id} className="group grid grid-cols-[minmax(0,1fr)_70px_62px_28px] items-center gap-2 border-b border-border/60 px-1 py-2 text-xs">
              <div className="min-w-0">
                <p className="truncate font-medium tabular-nums">{order.symbol}</p>
                <p className="mt-1 flex items-center gap-1.5">
                  <span className={order.side === "buy" ? "rounded bg-up/10 px-1.5 py-0.5 text-[10px] font-medium text-up" : "rounded bg-down/10 px-1.5 py-0.5 text-[10px] font-medium text-down"}>
                    {order.side === "buy" ? "买入" : "卖出"}
                  </span>
                  <span className="text-[10px] text-muted-foreground">{order.order_type === "limit" ? "限价" : "市价"}</span>
                </p>
              </div>
              <div className="text-right tabular-nums">
                <p>{order.price ? formatPrice(order.price) : "市价"}</p>
                <p className="text-muted-foreground">{formatVolume(order.volume)}</p>
              </div>
              <Badge
                variant="secondary"
                className="justify-center text-[10px]"
                title={order.reject_reason ?? undefined}
              >
                {ORDER_STATUS_LABELS[order.status] ?? order.status}
              </Badge>
              {CANCELLABLE_STATUSES.includes(order.status) ? (
                <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setCancelId(order.id)} title="撤单"><Ban className="h-3.5 w-3.5 text-danger" /></Button>
              ) : <span />}
            </div>
          )) : <PanelEmpty icon={<Ban className="h-7 w-7" />} text="暂无订单" />}
        </TabsContent>

        <TabsContent value="positions" className="mt-2 flex-1 overflow-y-auto px-2 pb-2">
          {positionsLoading ? <PanelLoading /> : positions.length ? positions.map((position) => (
            <div key={`${position.broker_account_id}-${position.symbol}`} className="grid grid-cols-[minmax(0,1fr)_72px_72px] gap-2 border-b border-border/60 px-2 py-2 text-xs">
              <span className="truncate font-medium tabular-nums">{position.symbol}</span>
              <span
                className="text-right tabular-nums"
                title={
                  Number(position.pending_settlement_volume) > 0
                    ? `T+1 待交收 ${formatVolume(position.pending_settlement_volume)}`
                    : Number(position.frozen_volume) > 0
                      ? `冻结 ${formatVolume(position.frozen_volume)}`
                      : undefined
                }
              >
                {formatVolume(
                  String(Number(position.available_volume) - Number(position.frozen_volume))
                )}
              </span>
              <span className="text-right tabular-nums text-muted-foreground">{formatPrice(position.avg_cost)}</span>
            </div>
          )) : <PanelEmpty icon={<Wallet className="h-7 w-7" />} text="暂无持仓" />}
        </TabsContent>
      </Tabs>

      <AlertDialog open={cancelId !== null} onOpenChange={(open) => !open && setCancelId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认撤销该订单？</AlertDialogTitle>
            <AlertDialogDescription>已成交部分不会被撤销。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => cancelId && cancelMutation.mutate(cancelId)}>确认撤单</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function PanelLoading() {
  return <div className="space-y-2 p-3">{Array.from({ length: 5 }).map((_, index) => <div key={index} className="h-10 animate-pulse rounded bg-muted" />)}</div>;
}

interface PanelEmptyProps {
  icon: React.ReactNode;
  text: string;
  href?: string;
  action?: string;
}

function PanelEmpty({ icon, text, href, action }: PanelEmptyProps) {
  return <div className="flex h-48 flex-col items-center justify-center gap-2 text-muted-foreground">{icon}<p className="text-xs">{text}</p>{href && action && <Button variant="secondary" size="sm" asChild><Link href={href}>{action}</Link></Button>}</div>;
}
