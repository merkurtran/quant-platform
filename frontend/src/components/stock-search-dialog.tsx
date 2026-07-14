"use client";

import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, X, Loader2 } from "lucide-react";
import { marketService } from "@/services/market";
import { cn } from "@/lib/utils";
import type { StockSearchResult } from "@/types";

interface StockSearchDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (stock: StockSearchResult) => void;
  title?: string;
}

const FILTERS = [
  { key: "all", label: "全部" },
  { key: "sh", label: "沪市" },
  { key: "sz", label: "深市" },
  { key: "bj", label: "北交所" },
];

export function StockSearchDialog({
  open,
  onOpenChange,
  onSelect,
  title = "股票搜索",
}: StockSearchDialogProps) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [filter, setFilter] = useState("all");
  const [highlightIndex, setHighlightIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      const timer = window.setTimeout(() => {
        setQuery("");
        setDebounced("");
        setHighlightIndex(0);
        inputRef.current?.focus();
      }, 50);

      return () => window.clearTimeout(timer);
    }
  }, [open]);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: results, isLoading } = useQuery({
    queryKey: ["stock-search-dialog", debounced],
    queryFn: () => marketService.searchStocks(debounced, 50),
    enabled: debounced.length >= 1 && open,
    staleTime: 30_000,
  });

  const filtered = (results ?? []).filter((s) => {
    if (filter === "all") return true;
    if (filter === "sh") return s.symbol.endsWith(".SH");
    if (filter === "sz") return s.symbol.endsWith(".SZ");
    if (filter === "bj") return s.symbol.endsWith(".BJ");
    return true;
  });

  const handleSelect = (stock: StockSearchResult) => {
    onSelect(stock);
    onOpenChange(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (filtered.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => Math.min(i + 1, filtered.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      handleSelect(filtered[highlightIndex]);
    } else if (e.key === "Escape") {
      onOpenChange(false);
    }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/40 pt-20">
      <div className="w-[600px] max-w-[90vw] overflow-hidden rounded-xl bg-popover shadow-2xl">
        {/* 标题栏 */}
        <div className="flex items-center justify-between px-5 pt-4">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            onClick={() => onOpenChange(false)}
            className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* 搜索框 */}
        <div className="px-5 pt-3">
          <div className="flex items-center gap-2 rounded-lg bg-muted px-3 py-2 transition-colors focus-within:bg-accent">
            <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setHighlightIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="输入代码或名称搜索..."
              className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
            />
            {isLoading && (
              <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
            )}
          </div>
        </div>

        {/* 筛选 Tab */}
        <div className="flex gap-1 px-5 pt-3">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              onClick={() => {
                setFilter(f.key);
                setHighlightIndex(0);
              }}
              className={cn(
                "rounded-full px-3 py-0.5 text-xs font-medium transition-colors",
                filter === f.key
                  ? "bg-foreground text-background"
                  : "text-muted-foreground hover:bg-accent"
              )}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* 结果列表 */}
        <div className="mt-3 max-h-96 overflow-y-auto">
          {!debounced ? (
            <div className="px-5 pb-6 pt-2 text-center text-sm text-muted-foreground">
              输入代码或名称开始搜索
            </div>
          ) : filtered.length === 0 && !isLoading ? (
            <div className="px-5 pb-6 pt-2 text-center text-sm text-muted-foreground">
              未找到匹配的股票
            </div>
          ) : (
            <ul>
              {filtered.map((stock, i) => (
                <li key={stock.symbol}>
                  <button
                    onClick={() => handleSelect(stock)}
                    onMouseEnter={() => setHighlightIndex(i)}
                    className={cn(
                      "flex w-full items-center gap-3 px-5 py-2.5 text-left text-sm transition-colors",
                      i === highlightIndex
                        ? "bg-accent"
                        : "hover:bg-accent/50"
                    )}
                  >
                    <span className="w-32 shrink-0 font-medium tabular-nums text-primary">
                      {stock.symbol}
                    </span>
                    <span className="flex-1 truncate text-foreground">
                      {stock.name}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
