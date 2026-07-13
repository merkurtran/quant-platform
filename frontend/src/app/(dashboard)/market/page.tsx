"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Plus,
  Search,
  MoreHorizontal,
  Maximize2,
  Minimize2,
  Sun,
  Moon,
} from "lucide-react";
import { marketService } from "@/services/market";
import { aiService } from "@/services/ai";
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
import { ADJUST_OPTIONS } from "@/constants";
import { useMarketSocket } from "@/hooks/use-market-socket";
import { formatPrice, priceColor, formatPercent } from "@/lib/format";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import type { Watchlist } from "@/types";

const QUICK_PERIODS = [
  { value: "1d", label: "1D" },
  { value: "5d", label: "5D" },
  { value: "1m", label: "1M" },
  { value: "3m", label: "3M" },
  { value: "6m", label: "6M" },
  { value: "1y", label: "1Y" },
  { value: "5y", label: "5Y" },
  { value: "all", label: "All" },
];

export default function MarketPage() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();

  const symbol = searchParams.get("symbol");
  const [period, setPeriod] = useState("1d");
  const [adjust, setAdjust] = useState("qfq");
  const [livePrice, setLivePrice] = useState<number | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const [searchValue, setSearchValue] = useState("");

  // 主题切换
  const [theme, setTheme] = useState<"light" | "dark">("light");
  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
  }, [theme]);

  // Watchlist
  const [createOpen, setCreateOpen] = useState(false);
  const [addOpen, setAddOpen] = useState<number | null>(null);
  const [newListName, setNewListName] = useState("");
  const [addSymbol, setAddSymbol] = useState("");
  const [addName, setAddName] = useState("");
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

  useMarketSocket({
    onQuote: (msg) => {
      if (msg.symbol === symbol) setLivePrice(msg.price);
    },
  });

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLivePrice(null);
  }, [symbol]);

  // AI 分析
  const { data: conversations } = useQuery({
    queryKey: ["conversations"],
    queryFn: aiService.listConversations,
  });
  const [activeConvId, setActiveConvId] = useState<number | null>(null);
  const { data: aiMessages } = useQuery({
    queryKey: ["messages", activeConvId],
    queryFn: () => aiService.listMessages(activeConvId!),
    enabled: !!activeConvId,
  });

  useEffect(() => {
    if (!activeConvId && conversations?.[0]) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setActiveConvId(conversations[0].id);
    }
  }, [conversations, activeConvId]);

  const sendAiMutation = useMutation({
    mutationFn: (content: string) =>
      aiService.sendMessage(activeConvId!, content),
  });

  const createConvMutation = useMutation({
    mutationFn: () => aiService.createConversation(),
    onSuccess: (conv) => {
      queryClient.invalidateQueries({ queryKey: ["conversations"] });
      setActiveConvId(conv.id);
    },
  });

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
      setAddSymbol("");
      setAddName("");
      toast.success("添加成功");
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

  // AI 默认问题
  const handleAiAsk = (question: string) => {
    if (!activeConvId) return;
    sendAiMutation.mutate(question);
  };

  return (
    <div className="flex h-[calc(100vh-3rem)] overflow-hidden bg-background text-foreground">
      {/* ── 主区（K线 + 周期） ── */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* 顶部信息栏 */}
        <div className="flex h-12 items-center gap-4 border-b border-border px-4">
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
                      {change.toFixed(2)} ({changePct && formatPercent(changePct)})
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
            onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            title="切换主题"
          >
            {theme === "light" ? (
              <Moon className="h-4 w-4" />
            ) : (
              <Sun className="h-4 w-4" />
            )}
          </Button>
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

        {/* K 线图区域 */}
        <div className="flex-1 overflow-hidden p-2">
          {symbol ? (
            klineLoading ? (
              <div className="h-full animate-pulse rounded-md bg-secondary" />
            ) : klineData && klineData.items.length > 0 ? (
              <KlineChart data={klineData.items} />
            ) : (
              <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                暂无 K 线数据（可手动执行{" "}
                <code className="rounded bg-secondary px-1">
                  fetch_daily_kline(&apos;{symbol.split(".")[0]}&apos;)
                </code>{" "}
                同步）
              </div>
            )
          ) : (
            <div className="flex h-full flex-col items-center justify-center gap-4 p-4">
              <div className="w-full max-w-sm space-y-4 text-center">
                <p className="text-sm text-muted-foreground">选择股票查看 K 线</p>
                <div className="flex items-center gap-2 rounded-lg border border-border bg-secondary px-3 py-2">
                  <Search className="h-4 w-4 text-muted-foreground" />
                  <Input
                    autoFocus
                    placeholder="输入代码，如 600519.SH"
                    className="h-8 border-0 bg-transparent focus-visible:ring-0"
                    value={searchValue}
                    onChange={(e) => setSearchValue(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && searchValue.trim()) {
                        selectSymbol(searchValue.trim());
                        setSearchValue("");
                      }
                    }}
                  />
                </div>
              </div>
            </div>
          )}
        </div>

        {/* 周期切换 - 底部 */}
        <div className="flex h-10 items-center gap-1 border-t border-border px-2">
          {QUICK_PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={cn(
                "rounded px-2.5 py-1 text-xs font-medium transition-colors",
                period === p.value
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              {p.label}
            </button>
          ))}
          <div className="ml-2 h-4 w-px bg-border" />
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

      {/* ── 右侧 Watchlist + AI ── */}
      {!fullscreen && (
        <aside className="flex w-80 shrink-0 flex-col border-l border-border bg-background">
          {/* Watchlist - 占上半部分 */}
          <div className="flex h-1/2 flex-col overflow-hidden border-b border-border">
            {/* 顶栏 */}
            <div className="flex h-10 items-center justify-between border-b border-border px-3">
              <h3 className="text-xs font-semibold">自选股</h3>
              <div className="flex gap-0.5">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-6 w-6"
                  onClick={() => setCreateOpen(true)}
                >
                  <Plus className="h-3.5 w-3.5" />
                </Button>
                <Button variant="ghost" size="icon" className="h-6 w-6">
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            {/* Tab 切换 */}
            {watchlists && watchlists.length > 0 && (
              <div className="flex overflow-x-auto border-b border-border bg-secondary/30">
                {watchlists.map((wl: Watchlist) => (
                  <button
                    key={wl.id}
                    onClick={() => setActiveListId(wl.id)}
                    className={cn(
                      "border-b-2 px-3 py-1.5 text-xs font-medium transition-colors whitespace-nowrap",
                      wl.id === (activeListId ?? watchlists[0].id)
                        ? "border-primary text-primary"
                        : "border-transparent text-muted-foreground hover:text-foreground"
                    )}
                  >
                    {wl.name}
                  </button>
                ))}
              </div>
            )}

            {/* 表头 */}
            {currentList && currentList.items.length > 0 && (
              <div className="grid grid-cols-12 gap-2 border-b border-border px-3 py-1 text-[10px] uppercase tracking-wide text-muted-foreground">
                <div className="col-span-5">Symbol</div>
                <div className="col-span-3 text-right">Last</div>
                <div className="col-span-4 text-right">Chg%</div>
              </div>
            )}

            {/* 列表 */}
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
                currentList?.items.map((item) => {
                  const isActive = item.symbol === symbol;
                  return (
                    <div
                      key={item.symbol}
                      className={cn(
                        "group grid cursor-pointer grid-cols-12 gap-2 border-b border-border/50 px-3 py-1.5 text-xs transition-colors",
                        isActive
                          ? "border-l-2 border-l-primary bg-primary/5"
                          : "hover:bg-secondary"
                      )}
                      onClick={() => selectSymbol(item.symbol)}
                    >
                      <div className="col-span-5 truncate">
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
                      <div className="col-span-3 text-right tabular-nums text-muted-foreground">
                        --
                      </div>
                      <div className="col-span-3 text-right tabular-nums text-muted-foreground">
                        --
                      </div>
                      <div className="col-span-1 flex items-center justify-end opacity-0 group-hover:opacity-100">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            removeItemMutation.mutate({
                              watchlistId: currentList.id,
                              sym: item.symbol,
                            });
                          }}
                          className="text-muted-foreground hover:text-danger"
                        >
                          ×
                        </button>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* 底部添加 */}
            {currentList && (
              <div className="border-t border-border p-1.5">
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

          {/* AI 分析 - 占下半部分 */}
          <div className="flex h-1/2 flex-col overflow-hidden">
            <div className="flex h-10 items-center justify-between border-b border-border px-3">
              <h3 className="text-xs font-semibold">AI 分析</h3>
              {symbol && (
                <span className="text-[10px] text-muted-foreground">{symbol}</span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto p-3">
              {!activeConvId ? (
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p>新建对话以开始 AI 分析</p>
                  <Button
                    size="sm"
                    className="w-full"
                    onClick={() => createConvMutation.mutate()}
                    disabled={createConvMutation.isPending}
                  >
                    <Plus className="h-3.5 w-3.5" />
                    新建对话
                  </Button>
                </div>
              ) : aiMessages && aiMessages.length > 0 ? (
                <div className="space-y-2">
                  {aiMessages.slice(-3).map((m) => (
                    <div
                      key={m.id}
                      className={cn(
                        "rounded p-2 text-xs",
                        m.role === "user"
                          ? "bg-primary/10"
                          : m.role === "tool"
                          ? "bg-muted text-[10px]"
                          : "bg-secondary"
                      )}
                    >
                      {m.role === "tool" ? (
                        <span className="text-muted-foreground">
                          [工具调用] {m.content.tool_name}
                        </span>
                      ) : (
                        <p className="whitespace-pre-wrap break-words">
                          {m.content.text?.slice(0, 200)}
                          {(m.content.text?.length ?? 0) > 200 ? "..." : ""}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground">
                    {symbol ? "询问 AI 关于当前股票" : "选择股票后可让 AI 分析"}
                  </p>
                  {symbol && (
                    <div className="flex flex-col gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 justify-start text-xs"
                        onClick={() => handleAiAsk(`分析 ${symbol} 最近的走势`)}
                        disabled={sendAiMutation.isPending}
                      >
                        分析最近走势
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 justify-start text-xs"
                        onClick={() =>
                          handleAiAsk(`${symbol} 当前估值是否合理`)
                        }
                        disabled={sendAiMutation.isPending}
                      >
                        估值分析
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 justify-start text-xs"
                        onClick={() =>
                          handleAiAsk(`给 ${symbol} 写一个回测策略`)
                        }
                        disabled={sendAiMutation.isPending}
                      >
                        写个回测策略
                      </Button>
                    </div>
                  )}
                </div>
              )}
              {sendAiMutation.isPending && (
                <p className="mt-2 text-[10px] text-muted-foreground">
                  AI 思考中...
                </p>
              )}
            </div>
          </div>
        </aside>
      )}

      {/* Dialogs */}
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

      <Dialog open={addOpen !== null} onOpenChange={() => setAddOpen(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>添加股票</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="symbol">股票代码 *</Label>
              <Input
                id="symbol"
                placeholder="如：600519.SH"
                value={addSymbol}
                onChange={(e) => setAddSymbol(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="name">股票名称（可选）</Label>
              <Input
                id="name"
                placeholder="如：贵州茅台"
                value={addName}
                onChange={(e) => setAddName(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              onClick={() => {
                if (addOpen !== null && addSymbol.trim()) {
                  addItemMutation.mutate({
                    watchlistId: addOpen,
                    data: {
                      symbol: addSymbol.trim(),
                      name: addName.trim() || undefined,
                    },
                  });
                }
              }}
              disabled={!addSymbol.trim() || addItemMutation.isPending}
            >
              添加
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
