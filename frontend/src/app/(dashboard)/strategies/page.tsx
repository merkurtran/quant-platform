"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Code2, Plus, Trash2, Pencil, Play } from "lucide-react";
import { strategyService } from "@/services/strategies";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
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
import { STRATEGY_STATUS_LABELS } from "@/constants";
import { formatDateTime } from "@/lib/format";
import { toast } from "sonner";

const STATUS_VARIANT: Record<string, "default" | "secondary" | "success" | "warning"> = {
  draft: "secondary",
  backtested: "default",
  paper_running: "success",
  archived: "warning",
};

export default function StrategiesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [deleteId, setDeleteId] = useState<number | null>(null);

  const { data: strategies, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: strategyService.list,
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => strategyService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      setDeleteId(null);
      toast.success("已删除");
    },
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">策略</h1>
        <Button onClick={() => router.push("/strategies/new")}>
          <Plus className="h-4 w-4" />
          新建策略
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <TableSkeleton key={i} rows={2} cols={2} />
          ))}
        </div>
      ) : !strategies || strategies.length === 0 ? (
        <EmptyState
          icon={Code2}
          title="还没有策略"
          description="创建你的第一个量化策略，编写 backtrader 代码并回测"
          action={
            <Button onClick={() => router.push("/strategies/new")}>
              <Plus className="h-4 w-4" />
              新建策略
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {strategies.map((s) => (
            <Card key={s.id} className="hover:shadow-sm transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-start justify-between">
                  <Link href={`/strategies/${s.id}`} className="flex-1">
                    <h3 className="font-semibold text-foreground hover:text-primary">
                      {s.name}
                    </h3>
                    <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                      {s.description ?? "无描述"}
                    </p>
                  </Link>
                  <Badge variant={STATUS_VARIANT[s.status] ?? "secondary"} className="ml-2 shrink-0">
                    {STRATEGY_STATUS_LABELS[s.status] ?? s.status}
                  </Badge>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {formatDateTime(s.updated_at)}
                  </span>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" asChild>
                      <Link href={`/market?panel=backtest&strategyId=${s.id}`} title="回测">
                        <Play className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button variant="ghost" size="icon" asChild>
                      <Link href={`/strategies/${s.id}`} title="编辑">
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => setDeleteId(s.id)}
                    >
                      <Trash2 className="h-4 w-4 text-danger" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除？</AlertDialogTitle>
            <AlertDialogDescription>
              删除策略将同时删除其所有回测记录，此操作不可撤销。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => deleteId && deleteMutation.mutate(deleteId)}
              disabled={deleteMutation.isPending}
            >
              删除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
