import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { QuoteMessage } from "@/types";

interface MarketState {
  selectedSymbol: string | null;
  quotes: Record<string, QuoteMessage>;
  subscribedSymbols: string[];
  _hasHydrated: boolean;
  setSelectedSymbol: (symbol: string) => void;
  setQuote: (quote: QuoteMessage) => void;
  setQuotes: (quotes: QuoteMessage[]) => void;
  subscribe: (symbols: string[]) => void;
  _setHasHydrated: (value: boolean) => void;
}

function toNum(v: unknown): number | null | undefined {
  if (v === null || v === undefined) return v as null | undefined;
  const n = Number(v);
  return Number.isNaN(n) ? undefined : n;
}

function mergeQuote(
  current: QuoteMessage | undefined,
  incoming: QuoteMessage
): QuoteMessage {
  const price = toNum(incoming.price) as number;
  const previousClose =
    incoming.previous_close != null
      ? toNum(incoming.previous_close)
      : current?.previous_close;
  const changeRaw =
    incoming.change != null
      ? toNum(incoming.change)
      : undefined;
  const derivedChange =
    previousClose != null ? price - previousClose : undefined;
  const change: number | null | undefined =
    changeRaw ?? derivedChange ?? current?.change;

  const changePctRaw =
    incoming.change_pct != null
      ? toNum(incoming.change_pct)
      : undefined;
  const derivedChangePct =
    change != null && previousClose
      ? (change / previousClose) * 100
      : undefined;
  const change_pct: number | null | undefined =
    changePctRaw ?? derivedChangePct ?? current?.change_pct;

  return {
    ...current,
    ...incoming,
    price,
    previous_close: previousClose,
    change,
    change_pct,
  };
}

function currentQuoteIsNewer(
  current: QuoteMessage | undefined,
  incoming: QuoteMessage
): boolean {
  if (!current) return false;
  const currentTimestamp = Date.parse(current.ts);
  const incomingTimestamp = Date.parse(incoming.ts);
  return (
    !Number.isNaN(currentTimestamp) &&
    !Number.isNaN(incomingTimestamp) &&
    currentTimestamp > incomingTimestamp
  );
}

export const useMarketStore = create<MarketState>()(
  persist(
    (set) => ({
      selectedSymbol: null,
      quotes: {},
      subscribedSymbols: [],
      _hasHydrated: false,
      setSelectedSymbol: (selectedSymbol) => set({ selectedSymbol }),
      setQuote: (quote) =>
        set((state) => {
          const current = state.quotes[quote.symbol];
          return {
            quotes: {
              ...state.quotes,
              [quote.symbol]: currentQuoteIsNewer(current, quote)
                ? mergeQuote(quote, current)
                : mergeQuote(current, quote),
            },
          };
        }),
      setQuotes: (quotes) =>
        set((state) => {
          const merged = { ...state.quotes };
          for (const quote of quotes) {
            const current = merged[quote.symbol];
            merged[quote.symbol] = currentQuoteIsNewer(current, quote)
              ? mergeQuote(quote, current)
              : mergeQuote(current, quote);
          }
          return { quotes: merged };
        }),
      subscribe: (symbols) =>
        set((state) => {
          const next = Array.from(
            new Set([...state.subscribedSymbols, ...symbols])
          );
          return next.length === state.subscribedSymbols.length
            ? state
            : { subscribedSymbols: next };
        }),
      _setHasHydrated: (_hasHydrated) => set({ _hasHydrated }),
    }),
    {
      name: "quant-market",
      partialize: (state) => ({ selectedSymbol: state.selectedSymbol }),
      onRehydrateStorage: () => (state) => state?._setHasHydrated(true),
    }
  )
);
