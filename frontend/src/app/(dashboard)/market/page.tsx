"use client";

import { useState, useEffect, useMemo } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, Plus, Maximize2, Minimize2, Search } from "lucide-react";
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
import { StockAnalysisPanel } from "@/components/panels/stock-analysis-panel";
import { StrategyBacktestPanel } from "@/components/panels/strategy-backtest-panel";
import {
  BacktestResult,
  type BacktestResultViewModel,
} from "@/components/panels/backtest-result";
import { TradingPanel } from "@/components/panels/trading-panel";
import { ADJUST_OPTIONS } from "@/constants";
import { useMarketStore } from "@/stores/market";
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
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const routeSymbol = searchParams.get("symbol");
  const panel = searchParams.get("panel");
  const selectedSymbol = useMarketStore((state) => state.selectedSymbol);
  const quotes = useMarketStore((state) => state.quotes);
  const hasMarketHydrated = useMarketStore((state) => state._hasHydrated);
  const setSelectedSymbol = useMarketStore((state) => state.setSelectedSymbol);
  const setQuotes = useMarketStore((state) => state.setQuotes);
  const subscribe = useMarketStore((state) => state.subscribe);
  const [period, setPeriod] = useState("1d");
  const [adjust, setAdjust] = useState("qfq");
  const [fullscreen, setFullscreen] = useState(false);
  const [backtestResult, setBacktestResult] = useState<BacktestResultViewModel | null>(null);

  // 搜索弹窗（空状态下引导选股 / 添加股票）
  const [pickerOpen, setPickerOpen] = useState(false);
  const [addOpen, setAddOpen] = useState<number | null>(null);

  // Watchlist
  const [createOpen, setCreateOpen] = useState(false);
  const [newListName, setNewListName] = useState("");
  const [collapsedListIds, setCollapsedListIds] = useState<Set<number>>(
    () => new Set()
  );

  const { data: watchlists, isLoading: wlLoading } = useQuery({
    queryKey: ["watchlists"],
    queryFn: marketService.getWatchlists,
  });

  const firstWatchlistSymbol = watchlists
    ?.flatMap((list) => list.items)
    .at(0)?.symbol;
  const symbol = routeSymbol ?? selectedSymbol ?? firstWatchlistSymbol ?? null;
  const stockName = useMemo(
    () =>
      watchlists
        ?.flatMap((list) => list.items)
        .find((item) => item.symbol === symbol)?.name ?? null,
    [symbol, watchlists]
  );
  const resolvingInitialSymbol = !hasMarketHydrated || (wlLoading && !symbol);
  const watchlistSymbols = useMemo(
    () =>
      Array.from(
        new Set(
          watchlists?.flatMap((list) =>
            list.items.map((item) => item.symbol)
          ) ?? []
        )
      ),
    [watchlists]
  );

  const { data: quoteSnapshots } = useQuery({
    queryKey: ["quote-snapshots", watchlistSymbols],
    queryFn: () => marketService.getQuotes(watchlistSymbols),
    enabled: watchlistSymbols.length > 0,
    staleTime: 60_000,
  });

  useEffect(() => {
    if (quoteSnapshots?.length) setQuotes(quoteSnapshots);
  }, [quoteSnapshots, setQuotes]);

  // URL 用于可分享链接，store 用于跨页面保留最后一次选择。
  useEffect(() => {
    if (!hasMarketHydrated || !symbol) return;
    if (selectedSymbol !== symbol) setSelectedSymbol(symbol);
    if (!routeSymbol) {
      const params = new URLSearchParams(searchParams);
      params.set("symbol", symbol);
      router.replace(`/market?${params.toString()}`);
    }
  }, [
    hasMarketHydrated,
    routeSymbol,
    router,
    searchParams,
    selectedSymbol,
    setSelectedSymbol,
    symbol,
  ]);

  // K 线
  const { data: klineData, isLoading: klineLoading } = useQuery({
    queryKey: ["klines", symbol, period, adjust],
    queryFn: () =>
      marketService.getKlines({ symbol: symbol!, period, adjust, limit: 300 }),
    enabled: !!symbol,
  });

  useEffect(() => {
    if (watchlistSymbols.length) subscribe(watchlistSymbols);
  }, [watchlistSymbols, subscribe]);

  const selectSymbol = (sym: string) => {
    setBacktestResult(null);
    setSelectedSymbol(sym);
    const params = new URLSearchParams(searchParams);
    params.set("symbol", sym);
    params.delete("runId");
    router.replace(`/market?${params.toString()}`);
  };

  const selectedQuote = symbol ? quotes[symbol] : undefined;
  const lastClose = klineData?.items?.[klineData.items.length - 1]?.close;
  const displayPrice =
    selectedQuote?.price ?? (lastClose ? parseFloat(lastClose) : null);
  const previousKlineClose = klineData?.items?.[klineData.items.length - 2]?.close;
  const prevClose =
    selectedQuote?.previous_close ??
    (previousKlineClose ? parseFloat(previousKlineClose) : null);
  const change =
    selectedQuote?.change ??
    (displayPrice !== null && prevClose
      ? displayPrice - prevClose
      : null);
  const changePct =
    selectedQuote?.change_pct ??
    (displayPrice !== null && prevClose
      ? ((displayPrice - prevClose) / prevClose) * 100
      : null);
  const showBacktestResult =
    panel === "backtest" &&
    backtestResult?.run.status === "success" &&
    backtestResult.run.result !== null;

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

  const toggleListCollapsed = (id: number) => {
    setCollapsedListIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  return (
    <div className="flex h-full gap-px overflow-hidden bg-border/70">
      {/* ── 主区（K线 + 周期） — 用浅灰缝隙分隔工具栏与图表 ── */}
      <div className="flex flex-1 flex-col gap-px overflow-hidden bg-border/60">
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
                      {Number(change).toFixed(2)} (
                      {changePct !== null ? formatPercent(changePct) : "--"})
                    </span>
                  )}
                </>
              )}
            </>
          ) : resolvingInitialSymbol ? (
            <div className="h-5 w-40 animate-pulse rounded bg-muted" />
          ) : (
            <h1 className="text-sm text-muted-foreground">未选择股票</h1>
          )}
          <div className="flex-1" />
          {!showBacktestResult && (
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
          )}
        </div>

        {/* K 线图区域 — 连续白色工作区 */}
        <div className="flex-1 overflow-hidden bg-card">
          {showBacktestResult ? (
            <BacktestResult backtest={backtestResult} />
          ) : symbol ? (
            <div className="h-full overflow-hidden bg-card">
              {klineLoading ? (
                <div className="h-full animate-pulse bg-muted/30" />
              ) : klineData && klineData.items.length > 0 ? (
                <KlineChart
                  key={`${symbol}-${period}-${adjust}`}
                  data={klineData.items}
                  symbol={symbol}
                />
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
          ) : resolvingInitialSymbol ? (
            <div className="h-full animate-pulse bg-muted/30" />
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-3 bg-card p-4">
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
        {!showBacktestResult && <div className="flex h-10 items-center gap-1 bg-card px-3">
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
        </div>}
      </div>

      {/* ── 右侧面板 — TradingView 风格白色信息栏 ── */}
      {!fullscreen && (
        <aside
          className={cn(
            "flex shrink-0 flex-col bg-card",
            panel === "backtest" || panel === "trading"
              ? "w-96"
              : "w-80"
          )}
        >
          {panel === "alerts" ? (
            <AlertPanel />
          ) : panel === "backtest" ? (
            <StrategyBacktestPanel
              key={symbol}
              symbol={symbol}
              onResultChange={setBacktestResult}
            />
          ) : panel === "trading" ? (
            <TradingPanel key={symbol} symbol={symbol} />
          ) : (
            <div className="flex h-full min-h-0 flex-col overflow-hidden">
              <div className="flex min-h-0 basis-[58%] flex-col overflow-hidden">
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

              <div className="grid h-8 grid-cols-[minmax(0,1fr)_64px_52px_52px] items-center gap-2 bg-muted/50 px-3 text-[11px] text-muted-foreground">
                <span>Symbol</span>
                <span className="text-right">Last</span>
                <span className="text-right">Chg</span>
                <span className="text-right">Chg%</span>
              </div>

              <div className="flex-1 overflow-y-auto">
                {wlLoading ? (
                  <div className="space-y-1 p-2">
                    {Array.from({ length: 8 }).map((_, i) => (
                      <div
                        key={i}
                        className="h-8 animate-pulse rounded bg-muted/70"
                      />
                    ))}
                  </div>
                ) : !watchlists || watchlists.length === 0 ? (
                  <div className="flex h-full flex-col items-center justify-center gap-2 px-3 text-center">
                    <p className="text-xs text-muted-foreground">
                      暂无自选股分组
                    </p>
                    <Button
                      variant="secondary"
                      size="sm"
                      className="h-7 text-xs"
                      onClick={() => setCreateOpen(true)}
                    >
                      <Plus className="h-3.5 w-3.5" />
                      新建分组
                    </Button>
                  </div>
                ) : (
                  <div>
                    {watchlists.map((wl: Watchlist) => {
                      const collapsed = collapsedListIds.has(wl.id);

                      return (
                        <section key={wl.id}>
                          <div className="flex h-8 items-center bg-muted/40 px-2">
                            <button
                              onClick={() => toggleListCollapsed(wl.id)}
                              className="flex min-w-0 flex-1 items-center gap-1 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
                            >
                              <ChevronDown
                                className={cn(
                                  "h-3.5 w-3.5 shrink-0 transition-transform",
                                  collapsed && "-rotate-90"
                                )}
                              />
                              <span className="truncate">{wl.name}</span>
                            </button>
                            <Button
                              variant="ghost"
                              size="icon"
                              className="h-6 w-6"
                              onClick={() => setAddOpen(wl.id)}
                              title="添加股票"
                            >
                              <Plus className="h-3.5 w-3.5" />
                            </Button>
                          </div>

                          {!collapsed &&
                            (wl.items.length === 0 ? (
                              <div className="px-6 py-3 text-xs text-muted-foreground">
                                暂无股票
                              </div>
                            ) : (
                              <ul>
                                {wl.items.map((item) => {
                                  const isActive = item.symbol === symbol;
                                  const itemQuote = quotes[item.symbol];
                                  const itemPrice =
                                    itemQuote?.price ??
                                    (isActive ? displayPrice : null);
                                  const itemChange =
                                    itemQuote?.change ??
                                    (isActive ? change : null);
                                  const itemChangePct =
                                    itemQuote?.change_pct ??
                                    (isActive ? changePct : null);

                                  return (
                                    <li
                                      key={item.symbol}
                                      onClick={() => selectSymbol(item.symbol)}
                                      className={cn(
                                        "group grid cursor-pointer grid-cols-[minmax(0,1fr)_64px_52px_52px] items-center gap-2 px-3 py-1.5 text-xs transition-colors hover:bg-accent",
                                        isActive &&
                                          "relative z-10 bg-card outline outline-1 -outline-offset-1 outline-foreground/70"
                                      )}
                                    >
                                      <div className="min-w-0">
                                        <div className="truncate font-medium tabular-nums">
                                          {item.symbol}
                                        </div>
                                        <div className="truncate text-[10px] text-muted-foreground">
                                          {item.name ?? "—"}
                                        </div>
                                      </div>
                                      <div className="text-right tabular-nums text-muted-foreground">
                                        {itemPrice != null
                                          ? formatPrice(itemPrice)
                                          : "--"}
                                      </div>
                                      <div
                                        className={cn(
                                          "text-right tabular-nums text-muted-foreground",
                                          itemChange !== null &&
                                            priceColor(itemChange)
                                        )}
                                      >
                                        {itemChange !== null
                                          ? `${itemChange > 0 ? "+" : ""}${itemChange.toFixed(2)}`
                                          : "--"}
                                      </div>
                                      <div
                                        className={cn(
                                          "relative text-right tabular-nums text-muted-foreground",
                                          itemChange !== null &&
                                            priceColor(itemChange)
                                        )}
                                      >
                                        {itemChangePct !== null
                                          ? formatPercent(itemChangePct)
                                          : "--"}
                                        <button
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            removeItemMutation.mutate({
                                              watchlistId: wl.id,
                                              sym: item.symbol,
                                            });
                                          }}
                                          className="absolute right-0 top-1/2 hidden -translate-y-1/2 bg-card px-1 text-sm text-muted-foreground hover:text-danger group-hover:block"
                                        >
                                          ×
                                        </button>
                                      </div>
                                    </li>
                                  );
                                })}
                              </ul>
                            ))}
                        </section>
                      );
                    })}
                  </div>
                )}
              </div>
              </div>
              <StockAnalysisPanel
                key={symbol ?? "empty"}
                symbol={symbol}
                stockName={stockName}
              />
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
