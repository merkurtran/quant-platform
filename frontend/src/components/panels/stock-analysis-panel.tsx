"use client";

import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { ArrowLeft, ArrowUpRight, Loader2, Newspaper, RefreshCw, Sparkles } from "lucide-react";
import { aiService } from "@/services/ai";
import { Button } from "@/components/ui/button";
import { StockAnalysisContent } from "@/components/panels/stock-analysis-content";
import type { StockAnalysis, StockNewsEvent } from "@/types";

interface StockAnalysisPanelProps {
  symbol: string | null;
  stockName?: string | null;
}

export function StockAnalysisPanel({ symbol, stockName }: StockAnalysisPanelProps) {
  const [selectedAnalysis, setSelectedAnalysis] = useState<{
    symbol: string;
    value: StockAnalysis;
  } | null>(null);

  const eventsQuery = useQuery({
    queryKey: ["ai-stock-events", symbol],
    queryFn: () => aiService.getStockEvents(symbol!, stockName),
    enabled: Boolean(symbol),
    staleTime: millisecondsUntilTomorrow(),
    gcTime: 25 * 60 * 60 * 1000,
    retry: false,
  });

  const analysisMutation = useMutation({
    mutationFn: (event: StockNewsEvent) =>
      aiService.analyzeStockEvent(symbol!, stockName, event),
    onSuccess: (value) => setSelectedAnalysis({ symbol: symbol!, value }),
  });

  const activeAnalysis =
    selectedAnalysis?.symbol === symbol
      ? selectedAnalysis.value
      : eventsQuery.data?.auto_analysis ?? null;
  const isEventDetail = selectedAnalysis?.symbol === symbol;

  return (
    <section className="flex min-h-0 flex-1 flex-col border-t">
      <div className="flex h-10 shrink-0 items-center gap-2 px-3">
        {isEventDetail ? (
          <Button
            variant="ghost"
            size="sm"
            className="h-7 gap-1 px-1.5 text-xs"
            onClick={() => setSelectedAnalysis(null)}
            title="返回事件列表"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            事件列表
          </Button>
        ) : (
          <Sparkles className="h-3.5 w-3.5 text-primary" />
        )}
        <h3 className="min-w-0 flex-1 truncate text-xs font-semibold">
          AI 个股分析{symbol ? ` · ${symbol}` : ""}
        </h3>
        {(eventsQuery.data?.cached || activeAnalysis?.cached) && (
          <span className="text-[10px] text-muted-foreground">缓存</span>
        )}
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={() => eventsQuery.refetch()}
          disabled={!symbol || eventsQuery.isFetching}
          title="刷新分析"
        >
          <RefreshCw className="h-3.5 w-3.5" />
        </Button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {!symbol ? (
          <EmptyState text="选择股票后查看 AI 事件分析" />
        ) : eventsQuery.isLoading ? (
          <div className="flex h-full items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在搜索最近 7 日公开信息
          </div>
        ) : eventsQuery.isError ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-5 text-center">
            <p className="text-xs leading-5 text-muted-foreground">
              {eventsQuery.error instanceof Error
                ? eventsQuery.error.message
                : "AI 分析暂时不可用"}
            </p>
            <Button size="sm" variant="outline" onClick={() => eventsQuery.refetch()}>
              重试
            </Button>
          </div>
        ) : analysisMutation.isPending ? (
          <div className="flex h-full items-center justify-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在核验事件影响
          </div>
        ) : analysisMutation.isError ? (
          <div className="flex h-full flex-col items-center justify-center gap-3 px-5 text-center">
            <p className="text-xs leading-5 text-muted-foreground">
              {analysisMutation.error instanceof Error
                ? analysisMutation.error.message
                : "事件分析暂时不可用"}
            </p>
            <Button size="sm" variant="outline" onClick={() => analysisMutation.reset()}>
              返回事件列表
            </Button>
          </div>
        ) : activeAnalysis ? (
          <StockAnalysisContent analysis={activeAnalysis} />
        ) : eventsQuery.data?.events.length ? (
          <div>
            {eventsQuery.data.events.map((event) => (
              <button
                key={event.event_id}
                className="group grid w-full grid-cols-[20px_minmax(0,1fr)_16px] gap-2 border-b px-3 py-3 text-left transition-colors hover:bg-muted/50"
                onClick={() => analysisMutation.mutate(event)}
              >
                <span className="flex h-5 w-5 items-center justify-center rounded bg-primary/10 text-primary">
                  <Newspaper className="h-3 w-3" />
                </span>
                <span className="min-w-0">
                  <span className="line-clamp-2 text-xs font-semibold leading-4">{event.title}</span>
                  <span className="mt-1 block line-clamp-2 text-[11px] leading-4 text-muted-foreground">{event.summary}</span>
                  <span className="mt-1.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                    <span className="rounded bg-muted px-1.5 py-0.5">{event.source_name}</span>
                    {event.published_at && <span>{dayjs(event.published_at).format("MM-DD HH:mm")}</span>}
                  </span>
                </span>
                <ArrowUpRight className="mt-0.5 h-3.5 w-3.5 text-muted-foreground transition-colors group-hover:text-primary" />
              </button>
            ))}
          </div>
        ) : (
          <EmptyState text="未找到可核验的分析结果" />
        )}
      </div>
    </section>
  );
}

function millisecondsUntilTomorrow() {
  const now = dayjs();
  return Math.max(now.endOf("day").diff(now) + 1, 1000);
}

function EmptyState({ text }: { text: string }) {
  return (
    <div className="flex h-full items-center justify-center px-5 text-center text-xs text-muted-foreground">
      {text}
    </div>
  );
}
