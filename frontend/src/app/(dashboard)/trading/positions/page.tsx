"use client";

import { useQuery } from "@tanstack/react-query";
import { Wallet } from "lucide-react";
import { tradingService } from "@/services/trading";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
import { formatPrice, formatVolume, formatDateTime } from "@/lib/format";

export default function PositionsPage() {
  const { data: positions, isLoading } = useQuery({
    queryKey: ["positions"],
    queryFn: tradingService.listPositions,
    refetchInterval: 2_000,
  });

  return (
    <div className="space-y-6 p-6">
      <h1 className="text-2xl font-bold">交易 · 持仓</h1>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={4} cols={5} />
            </div>
          ) : !positions || positions.length === 0 ? (
            <EmptyState
              icon={Wallet}
              title="暂无持仓"
              description="下单成交后将在此显示持仓信息"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>代码</TableHead>
                  <TableHead className="text-right">持仓量</TableHead>
                  <TableHead className="text-right">平均成本</TableHead>
                  <TableHead>更新时间</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {positions.map((p, i) => (
                  <TableRow key={`${p.broker_account_id}-${p.symbol}-${i}`}>
                    <TableCell className="font-medium tabular-nums">
                      {p.symbol}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatVolume(p.volume)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {formatPrice(p.avg_cost)}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground tabular-nums">
                      {formatDateTime(p.updated_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
