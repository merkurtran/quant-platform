"use client";

import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL } from "@/constants";
import { useAuthStore } from "@/stores/auth";
import type { QuoteMessage, AlertPushMessage } from "@/types";
import { toast } from "sonner";

interface UseMarketSocketOptions {
  onQuote?: (msg: QuoteMessage) => void;
  onAlert?: (msg: AlertPushMessage) => void;
}

export function useMarketSocket(options: UseMarketSocketOptions = {}) {
  const { onQuote, onAlert } = options;
  const token = useAuthStore((s) => s.accessToken);
  const [isConnected, setIsConnected] = useState(false);

  const onQuoteRef = useRef(onQuote);
  const onAlertRef = useRef(onAlert);
  const subscribedRef = useRef<Set<string>>(new Set());
  const wsRef = useRef<WebSocket | null>(null);

  // 同步最新回调
  useEffect(() => {
    onQuoteRef.current = onQuote;
    onAlertRef.current = onAlert;
  });

  // 连接 + 重连
  useEffect(() => {
    if (!token) return;

    let reconnectDelay = 0;
    let timer: ReturnType<typeof setTimeout>;
    let closed = false;

    const connect = () => {
      const ws = new WebSocket(`${WS_BASE_URL}?token=${token}`);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectDelay = 0;
        if (subscribedRef.current.size > 0) {
          ws.send(
            JSON.stringify({
              action: "subscribe",
              symbols: Array.from(subscribedRef.current),
            })
          );
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.event === "alert") {
            onAlertRef.current?.(data as AlertPushMessage);
            toast.warning(`告警触发：${data.symbol}`, {
              description: `触发价 ${data.trigger_value}`,
            });
            return;
          }
          if (data.event === "error") return;
          if (data.symbol && data.price !== undefined) {
            onQuoteRef.current?.(data as QuoteMessage);
          }
        } catch {
          // ignore
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        if (closed) return;
        // 指数退避
        reconnectDelay = reconnectDelay === 0 ? 1000 : Math.min(reconnectDelay * 2, 30000);
        timer = setTimeout(connect, reconnectDelay);
      };

      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      closed = true;
      clearTimeout(timer);
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [token]);

  const subscribe = (symbols: string[]) => {
    const newSymbols = symbols.filter((s) => !subscribedRef.current.has(s));
    if (newSymbols.length === 0) return;
    newSymbols.forEach((s) => subscribedRef.current.add(s));
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ action: "subscribe", symbols: newSymbols })
      );
    }
  };

  return { isConnected, subscribe };
}
