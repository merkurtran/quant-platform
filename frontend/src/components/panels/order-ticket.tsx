"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Loader2 } from "lucide-react";
import { tradingService } from "@/services/trading";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { BrokerAccount } from "@/types";

interface OrderTicketProps {
  accounts: BrokerAccount[];
  symbol: string | null;
}

export function OrderTicket({ accounts, symbol }: OrderTicketProps) {
  const queryClient = useQueryClient();
  const [accountId, setAccountId] = useState("");
  const [orderSymbol, setOrderSymbol] = useState(symbol ?? "");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState<"limit" | "market">("limit");
  const [price, setPrice] = useState("");
  const [volume, setVolume] = useState("");

  const selectedAccountId = accountId || accounts[0]?.id.toString() || "";

  const createMutation = useMutation({
    mutationFn: () =>
      tradingService.createOrder({
        broker_account_id: Number(selectedAccountId),
        symbol: orderSymbol,
        side,
        order_type: orderType,
        price: orderType === "limit" ? price : undefined,
        volume,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      queryClient.invalidateQueries({ queryKey: ["positions"] });
      queryClient.invalidateQueries({ queryKey: ["broker-accounts"] });
      setPrice("");
      setVolume("");
      toast.success("下单成功");
    },
  });

  const canSubmit =
    selectedAccountId && orderSymbol && volume && (orderType === "market" || price);

  return (
    <div className="space-y-3 p-3">
      <div className="grid grid-cols-2 gap-px rounded bg-muted p-0.5">
        {(["buy", "sell"] as const).map((value) => (
          <button
            key={value}
            type="button"
            aria-pressed={side === value}
            onClick={() => setSide(value)}
            className={cn(
              "h-8 rounded text-xs font-semibold transition-colors",
              side === value
                ? value === "buy"
                  ? "bg-up text-white shadow-sm"
                  : "bg-down text-white shadow-sm"
                : "text-muted-foreground hover:bg-card hover:text-foreground"
            )}
          >
            {value === "buy" ? "买入" : "卖出"}
          </button>
        ))}
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs">账户</Label>
        <Select value={selectedAccountId} onValueChange={setAccountId}>
          <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="选择账户" /></SelectTrigger>
          <SelectContent>
            {accounts.map((account) => (
              <SelectItem key={account.id} value={account.id.toString()}>{account.account_alias}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-1.5">
        <Label className="text-xs">股票代码</Label>
        <Input className="h-8 text-xs" value={orderSymbol} onChange={(event) => setOrderSymbol(event.target.value)} />
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1.5">
          <Label className="text-xs">订单类型</Label>
          <Select value={orderType} onValueChange={(value) => setOrderType(value as "limit" | "market")}>
            <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="limit">限价</SelectItem>
              <SelectItem value="market">市价</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">委托数量</Label>
          <Input className="h-8 text-xs" inputMode="decimal" value={volume} onChange={(event) => setVolume(event.target.value)} />
        </div>
      </div>

      {orderType === "limit" && (
        <div className="space-y-1.5">
          <Label className="text-xs">委托价格</Label>
          <Input className="h-8 text-xs" inputMode="decimal" value={price} onChange={(event) => setPrice(event.target.value)} />
        </div>
      )}

      <Button
        className={cn(
          "w-full font-semibold text-white",
          side === "buy" ? "bg-up hover:bg-up/90" : "bg-down hover:bg-down/90"
        )}
        size="sm"
        onClick={() => createMutation.mutate()}
        disabled={!canSubmit || createMutation.isPending}
      >
        {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
        {side === "buy" ? "买入" : "卖出"}
      </Button>
    </div>
  );
}
