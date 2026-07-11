"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function SymbolRedirectPage() {
  const params = useParams<{ symbol: string }>();
  const router = useRouter();

  useEffect(() => {
    const symbol = decodeURIComponent(params.symbol);
    router.replace(`/market?symbol=${encodeURIComponent(symbol)}`);
  }, [params.symbol, router]);

  return null;
}
