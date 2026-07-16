"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { useAuthStore } from "@/stores/auth";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      })
  );
  const userIdRef = useRef(useAuthStore.getState().user?.id ?? null);

  useEffect(
    () =>
      useAuthStore.subscribe((state) => {
        const nextUserId = state.user?.id ?? null;
        if (nextUserId !== userIdRef.current) {
          client.clear();
          userIdRef.current = nextUserId;
        }
      }),
    [client]
  );

  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}
