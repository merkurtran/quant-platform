"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Maximize2, Minimize2, Search } from "lucide-react";
import { marketService } from "@/services/market";
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { KlineChart } from "@/components/chart/kline-chart";
import { StockSearchDialog } from "@/components/stock-search-dialog";
import { AlertPanel } from "@/components/panels/alert-panel";
import { AIPanel } from "@/components/panels/ai-panel";
import { ADJUST_OPTIONS } from "@/constants";
import { useMarketSocket } from "@/hooks/use-market-socket";
import { formatPrice, priceColor, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { Watchlist, StockSearchResult } from "@/types";

const QUICK_PERIODS = [
  { value: "1m", label: "1m" },
  { value: "5m", label: "5m" },
  { value: "15m", label: "15m" },
  { value: "30m", label: "30m" },
  { value: "60m", label: "60m" },
  { value: "1d", label: "1D" },
  { value: "1w", label: "1W" },
  { value: "1M", label: "1M" },
];

export default function MarketPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const symbol = searchParams.get("symbol");
  const panel = searchParams.get("panel");
  const [period, setPeriod] = useState("1d");
  const [adjust, setAdjust] = useState("qfq");
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [livePrices, setLivePrices] = useState<Record<string, number>>({});
  const [fullscreen, setFullscreen] = useState(false);

  // 搜索弹窗（空状态下引导选股 / 添加股票）
  const [pickerOpen, setPickerOpen] = useState(false);
  const [addOpen, setAddOpen] = useState<number | null>(null);

  // Watchlist
  const [createOpen, setCreateOpen] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [activeListId, setActiveListId] = useState<number | null>(null);

  const { data: watchlists, isLoading: wlLoading } = useQuery({
    queryKey: ["watchlists"],
    queryFn: marketService.getWatchlists,
  });

  const currentList =
    watchlists?.find(
      (w: Watchlist) => w.id === (activeListId ?? watchlists?.[0]?.id)
    ) ?? null;

  // 自动选中：有自选股但 URL 没指定 symbol 时，选第一只
  useEffect(() => {
    if (!symbol && watchlists?.length && watchlists[0].items.length) {
      const firstSymbol = watchlists[0].items[0].symbol;
      const params = new URLSearchParams(searchParams);
      params.set("symbol", firstSymbol);
      router.replace(`${pathname}?${params.toString()}`);
    }
  }, [watchlists, symbol, searchParams, pathname, router]);

  // K 线
  const { data: klineData, isLoading: klineLoading } = useQuery({
    queryKey: ["klines", symbol, period, adjust],
    queryFn: () =>
      marketService.getKlines({ symbol: symbol!, period, adjust, limit: 300 }),
    enabled: !!symbol,
  });

  const { subscribe } = useMarketSocket({
    onQuote: (msg) => {
      setLivePrices((prev) => ({ ...prev, [msg.symbol]: msg.price }));
      if (msg.symbol === symbol) setLivePrice(msg.price);
    },
  });

  useEffect(() => {
    if (symbol) subscribe([symbol]);
  }, [symbol, subscribe]);

  useEffect(() => {
    if (currentList?.items.length) {
      subscribe(currentList.items.map((item) => item.symbol));
    }
  }, [currentList, subscribe]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLivePrice(null);
  }, [symbol]);

  const selectSymbol = (sym: string) => {
    const params = new URLSearchParams(searchParams);
    params.set("symbol", sym);
    router.replace(`${pathname}?${params.toString()}`);
  };

  const lastClose = klineData?.items?.[klineData.items.length - 1]?.close;
  const displayPrice = livePrice ?? (lastClose ? parseFloat(lastClose) : null);
  const prevClose = klineData?.items?.[klineData.items.length - 2]?.close;
  const change =
    displayPrice && prevClose ? displayPrice - parseFloat(prevClose) : null;
  const changePct =
    displayPrice && prevClose
      ? ((displayPrice - parseFloat(prevClose)) / parseFloat(prevClose)) * 100
      : null;

  // Watchlist mutations
  const createMutation = useMutation({
    mutationFn: (name: string) => marketService.createWatchlist(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      setCreateOpen(false);
      setNewListName("");
      toast.success("创建成功");
    },
  });
  const addItemMutation = useMutation({
    mutationFn: (p: {
      watchlistId: number;
      data: { symbol: string; name?: string };
    }) => marketService.addWatchlistItem(p.watchlistId, p.data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      setAddOpen(null);
      setPickerOpen(false);
      toast.success("添加成功");
    },
    onError: () => {
      // 失败时不关闭弹窗，让用户重试
    },
  });
  const removeItemMutation = useMutation({
    mutationFn: (p: { watchlistId: number; sym: string }) =>
      marketService.removeWatchlistItem(p.watchlistId, p.sym),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["watchlists"] });
      toast.success("已移除");
    },
  });

  const handleStockSelect = (stock: StockSearchResult) => {
    selectSymbol(stock.symbol);
  };

  const handleAddStock = (stock: StockSearchResult) => {
    if (addOpen !== null) {
      addItemMutation.mutate({
        watchlistId: addOpen,
        data: { symbol: stock.symbol, name: stock.name },
      });
    }
  };

  return (
    <div className="flex h-full overflow-hidden">
      {/* ── 主区（K线 + 周期） — 浅灰底，区别于侧边栏白底 ── */}
      <div className="flex flex-1 flex-col overflow-hidden bg-background">
        {/* 顶部信息栏 — 白底浮于浅灰底之上 */}
        <div className="flex h-12 items-center gap-4 bg-card px-4">
          {symbol ? (
            <>
              <h1 className="text-base font-bold">{symbol}</h1>
              {displayPrice !== null && (
                <>
                  <span
                    className={cn(
                      "text-xl font-bold tabular-nums",
                      priceColor(change)
                    )}
                  >
                    {formatPrice(displayPrice)}
                  </span>
                  {change !== null && (
                    <span
                      className={cn(
                        "text-sm tabular-nums",
                        priceColor(change)
                      )}
                    >
                      {change > 0 ? "+" : ""}
                      {change.toFixed(2)} (
                      {changePct && formatPercent(changePct)})
                    </span>
                  )}
                </>
              )}
            </>
          ) : (
            <h1 className="text-sm text-muted-foreground">未选择股票</h1>
          )}
          <div className="flex-1" />
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8"
            onClick={() => setFullscreen((v) => !v)}
            title="全屏 K 线"
          >
            {fullscreen ? (
              <Minimize2 className="h-4 w-4" />
            ) : (
              <Maximize2 className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* K 线图区域 — 白色卡片浮于灰底 */}
        <div className="flex-1 overflow-hidden p-2">
          {symbol ? (
            <div className="h-full overflow-hidden rounded-lg bg-card">
              {klineLoading ? (
                <div className="h-full animate-pulse bg-muted/30" />
              ) : klineData && klineData.items.length > 0 ? (
                <KlineChart data={klineData.items} />
              ) : (
                <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                  暂无 K 线数据（可手动执行{" "}
                  <code className="rounded bg-muted px-1">
                    fetch_daily_kline(&apos;{symbol.split(".")[0]}&apos;)
                  </code>{" "}
                  同步）
                </div>
              )}
            </div>
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 p-4">
              <p className="text-sm text-muted-foreground">
                选择股票查看 K 线
              </p>
              <Button onClick={() => setPickerOpen(true)}>
                <Search className="h-4 w-4" />
                搜索股票
              </Button>
            </div>
          )}
        </div>

        {/* 周期切换 - 底部，白底浮于灰底 */}
        <div className="flex h-10 items-center gap-1 bg-card px-3">
          {QUICK_PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={cn(
                "rounded px-2.5 py-1 text-xs font-medium transition-colors",
                period === p.value
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              )}
            >
              {p.label}
            </button>
          ))}
          <div className="ml-2 h-4 w-px bg-border/60" />
          <Select value={adjust} onValueChange={setAdjust}>
            <SelectTrigger className="h-7 w-20 border-0 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ADJUST_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* ── 右侧面板 — 白底卡（明显比主区深/浅一档） ── */}
      {!fullscreen && (
        <aside
          className={cn(
            "flex shrink-0 flex-col bg-card",
            panel === "ai" ? "w-96" : "w-80"
          )}
        >
          {panel === "alerts" ? (
            <AlertPanel />
          ) : panel === "ai" ? (
            <AIPanel />
          ) : (
            <div className="flex h-full flex-col overflow-hidden">
              {/* 顶栏 */}
              <div className="flex h-10 items-center justify-between px-3">
                <h3 className="text-xs font-semibold">自选股</h3>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
              </div>

              {/* Tab 切换 — 用 muted 背景色块分隔，无下划线 */}
              {watchlists && watchlists.length > 0 && (
                <div className="flex overflow-x-auto bg-muted/30 px-2 py-1">
                  {watchlists.map((wl: Watchlist) => (
                    <button
                      key={wl.id}
                      onClick={() => setActiveListId(wl.id)}
                      className={cn(
                        "rounded-full px-3 py-0.5 text-xs font-medium transition-colors whitespace-nowrap",
                        wl.id === (activeListId ?? watchlists[0].id)
                          ? "bg-card text-foreground shadow-sm"
                          : "text-muted-foreground hover:text-foreground"
                      )}
                    >
                      {wl.name}
                    </button>
                  ))}
                </div>
              )}

              {/* 列表 — 行间用 muted/30 交替色块，无 border-b */}
              <div className="flex-1 overflow-y-auto">
                {wlLoading ? (
                  <div className="p-3 text-center text-xs text-muted-foreground">
                    加载中...
                  </div>
                ) : currentList?.items.length === 0 ? (
                  <div className="px-3 py-6 text-center text-xs text-muted-foreground">
                    暂无股票
                  </div>
                ) : (
                  <ul>
                    {currentList?.items.map((item, i) => {
                      const isActive = item.symbol === symbol;
                      return (
                        <li
                          key={item.symbol}
                          onClick={() => selectSymbol(item.symbol)}
                          className={cn(
                            "group flex cursor-pointer items-center gap-2 px-3 py-1.5 text-xs transition-colors",
                            isActive
                              ? "bg-primary/10"
                              : i % 2 === 0
                              ? "hover:bg-accent"
                              : "bg-muted/20 hover:bg-accent"
                          )}
                        >
                          <div className="flex-1 truncate">
                            <div
                              className={cn(
                                "font-medium tabular-nums",
                                isActive && "text-primary"
                              )}
                            >
                              {item.symbol}
                            </div>
                            <div className="truncate text-[10px] text-muted-foreground">
                              {item.name ?? "—"}
                            </div>
                          </div>
                          <div className="w-16 text-right tabular-nums text-muted-foreground">
                            {livePrices[item.symbol] != null
                              ? formatPrice(livePrices[item.symbol])
                              : "--"}
                          </div>
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              removeItemMutation.mutate({
                                watchlistId: currentList.id,
                                sym: item.symbol,
                              });
                            }}
                            className="shrink-0 text-muted-foreground opacity-0 transition-opacity hover:text-danger group-hover:opacity-100"
                          >
                            ×
                          </button>
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>

              {/* 底部添加 */}
              {currentList && (
                <div className="bg-muted/30 p-1.5">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-7 w-full justify-start text-xs"
                    onClick={() => setAddOpen(currentList.id)}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    添加股票
                  </Button>
                </div>
              )}
            </div>
          )}
        </aside>
      )}

      {/* 股票搜索弹窗 — 用于空状态选股 & 添加股票 */}
      <StockSearchDialog
        open={pickerOpen || addOpen !== null}
        onOpenChange={(o) => {
          if (!o) {
            setPickerOpen(false);
            setAddOpen(null);
          }
        }}
        onSelect={(stock) => {
          if (addOpen !== null) {
            handleAddStock(stock);
          } else {
            handleStockSelect(stock);
          }
        }}
        title={addOpen !== null ? "添加股票到自选股" : "选择股票"}
      />

      {/* 新建自选股列表 Dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>新建自选股列表</DialogTitle>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="list-name">列表名称</Label>
            <Input
              id="list-name"
              placeholder="如：我的关注"
              value={newListName}
              onChange={(e) => setNewListName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && newListName.trim()) {
                  createMutation.mutate(newListName.trim());
                }
              }}
            />
          </div>
          <DialogFooter>
            <Button
              onClick={() =>
                newListName.trim() && createMutation.mutate(newListName.trim())
              }
              disabled={!newListName.trim() || createMutation.isPending}
            >
              创建
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
