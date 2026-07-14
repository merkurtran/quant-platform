"use client";

import { useEffect } from "react";
import { useMarketSocket } from "@/hooks/use-market-socket";
import { useMarketStore } from "@/stores/market";

interface MarketSocketProviderProps {
  children: React.ReactNode;
}

export function MarketSocketProvider({ children }: MarketSocketProviderProps) {
  const subscribedSymbols = useMarketStore((state) => state.subscribedSymbols);
  const setQuote = useMarketStore((state) => state.setQuote);
  const { subscribe } = useMarketSocket({ onQuote: setQuote });

  useEffect(() => {
    if (subscribedSymbols.length > 0) subscribe(subscribedSymbols);
  }, [subscribedSymbols, subscribe]);

  return children;
}
