"use client";

import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { Code2, Plus, Search } from "lucide-react";
import { strategyService } from "@/services/strategies";
import { StrategyCard } from "@/components/strategy/strategy-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/layout/empty-state";
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
import { toast } from "sonner";

type SortMode = "newest" | "oldest" | "name";

export default function StrategiesPage() {
  const queryClient = useQueryClient();
  const [deleteId, setDeleteId] = useState<number | null>(null);
  const [query, setQuery] = useState("");
  const [sortMode, setSortMode] = useState<SortMode>("newest");

  const { data: strategies, isLoading } = useQuery({
    queryKey: ["strategies"],
    queryFn: strategyService.list,
  });

  const visibleStrategies = useMemo(() => {
    const keyword = query.trim().toLowerCase();
    const filtered = (strategies ?? []).filter((strategy) =>
      `${strategy.name} ${strategy.description ?? ""}`.toLowerCase().includes(keyword)
    );
    return filtered.sort((a, b) => {
      if (sortMode === "name") return a.name.localeCompare(b.name, "zh-CN");
      const difference = Date.parse(a.updated_at) - Date.parse(b.updated_at);
      return sortMode === "oldest" ? difference : -difference;
    });
  }, [query, sortMode, strategies]);

  const deleteMutation = useMutation({
    mutationFn: strategyService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      setDeleteId(null);
      toast.success("策略已删除");
    },
  });

  return (
    <div className="h-full overflow-y-auto">
      <header className="flex items-center justify-between bg-card px-6 py-5">
        <div>
          <h1 className="text-2xl font-bold">我的策略</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            编写、管理并回测你的量化交易逻辑
          </p>
        </div>
        <Button asChild>
          <Link href="/strategies/new">
            <Plus className="h-4 w-4" />
            新建策略
          </Link>
        </Button>
      </header>

      <div className="flex items-center gap-3 bg-muted/30 px-6 py-4">
        <div className="relative w-full max-w-sm">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="pl-9"
            placeholder="搜索策略名称或描述"
          />
        </div>
        <Select value={sortMode} onValueChange={(value: SortMode) => setSortMode(value)}>
          <SelectTrigger className="w-32 bg-card">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">最近更新</SelectItem>
            <SelectItem value="oldest">最早更新</SelectItem>
            <SelectItem value="name">按名称</SelectItem>
          </SelectContent>
        </Select>
        <span className="ml-auto text-xs tabular-nums text-muted-foreground">
          {visibleStrategies.length} 个策略
        </span>
      </div>

      <main className="p-6">
        {isLoading ? (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {Array.from({ length: 6 }).map((_, index) => (
              <div key={index} className="h-52 animate-pulse rounded-lg bg-card" />
            ))}
          </div>
        ) : !strategies?.length ? (
          <EmptyState
            icon={Code2}
            title="还没有策略"
            description="创建第一个量化策略，编写 backtrader 代码并开始回测"
            action={
              <Button asChild>
                <Link href="/strategies/new">
                  <Plus className="h-4 w-4" />
                  新建策略
                </Link>
              </Button>
            }
          />
        ) : visibleStrategies.length === 0 ? (
          <div className="flex h-64 flex-col items-center justify-center gap-3 text-center">
            <Search className="h-10 w-10 text-muted-foreground" />
            <p className="font-semibold">没有匹配的策略</p>
            <Button variant="outline" size="sm" onClick={() => setQuery("")}>
              清除搜索
            </Button>
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
            {visibleStrategies.map((strategy) => (
              <StrategyCard key={strategy.id} strategy={strategy} onDelete={setDeleteId} />
            ))}
          </div>
        )}
      </main>

      <AlertDialog open={deleteId !== null} onOpenChange={() => setDeleteId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认删除策略？</AlertDialogTitle>
            <AlertDialogDescription>
              删除后相关回测记录也会一并移除，此操作不可撤销。
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
