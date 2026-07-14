"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import { Search, Loader2, X } from "lucide-react";
import { marketService } from "@/services/market";
import { cn } from "@/lib/utils";
import type { StockSearchResult } from "@/types";

interface StockSearchProps {
  onSelect: (stock: StockSearchResult) => void;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  clearOnSelect?: boolean;
}

export function StockSearch({
  onSelect,
  placeholder = "搜索股票代码或名称...",
  className,
  autoFocus,
  clearOnSelect = true,
}: StockSearchProps) {
  const [query, setQuery] = useState("");
  const [debounced, setDebounced] = useState("");
  const [open, setOpen] = useState(false);
  const [highlightIndex, setHighlightIndex] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(query.trim()), 300);
    return () => clearTimeout(timer);
  }, [query]);

  const { data: results, isLoading } = useQuery({
    queryKey: ["stock-search", debounced],
    queryFn: () => marketService.searchStocks(debounced),
    enabled: debounced.length >= 1,
    staleTime: 30_000,
  });

  const list = results ?? [];

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSelect = useCallback(
    (stock: StockSearchResult) => {
      onSelect(stock);
      if (clearOnSelect) {
        setQuery("");
        setDebounced("");
      }
      setOpen(false);
      inputRef.current?.blur();
    },
    [onSelect, clearOnSelect]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!open || list.length === 0) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setHighlightIndex((i) => Math.min(i + 1, list.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setHighlightIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      handleSelect(list[highlightIndex]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <div className="flex items-center gap-2 rounded-lg bg-muted/50 px-3 py-1.5 transition-colors focus-within:bg-muted">
        <Search className="h-4 w-4 shrink-0 text-muted-foreground" />
        <input
          ref={inputRef}
          autoFocus={autoFocus}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setHighlightIndex(0);
            setOpen(true);
          }}
          onFocus={() => query && setOpen(true)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          className="w-full bg-transparent text-sm outline-none placeholder:text-muted-foreground"
        />
        {query && (
          <button
            onClick={() => {
              setQuery("");
              setDebounced("");
              setHighlightIndex(0);
              inputRef.current?.focus();
            }}
            className="shrink-0 text-muted-foreground hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        )}
        {isLoading && (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-muted-foreground" />
        )}
      </div>

      {open && debounced && (
        <div className="absolute left-0 right-0 top-full z-50 mt-1.5 max-h-96 overflow-y-auto rounded-lg bg-popover shadow-lg">
          {list.length === 0 && !isLoading ? (
            <div className="px-4 py-8 text-center text-sm text-muted-foreground">
              未找到匹配的股票
            </div>
          ) : (
            <ul className="py-1">
              {list.map((stock, i) => (
                <li key={stock.symbol}>
                  <button
                    onClick={() => handleSelect(stock)}
                    onMouseEnter={() => setHighlightIndex(i)}
                    className={cn(
                      "flex w-full items-center justify-between gap-3 px-4 py-2.5 text-left text-sm transition-colors",
                      i === highlightIndex
                        ? "bg-accent"
                        : "hover:bg-accent/50"
                    )}
                  >
                    <span className="font-medium tabular-nums text-primary">
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
      )}
    </div>
  );
}
