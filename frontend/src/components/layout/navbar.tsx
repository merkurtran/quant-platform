"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, User, Wallet } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { toast } from "sonner";
import { StockSearch } from "@/components/stock-search";
import { useAuthStore } from "@/stores/auth";
import { useMarketStore } from "@/stores/market";
import { tradingService } from "@/services/trading";
import { formatMoney } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { StockSearchResult } from "@/types";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export function Navbar() {
  const router = useRouter();
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const selectedSymbol = useMarketStore((state) => state.selectedSymbol);
  const setSelectedSymbol = useMarketStore((state) => state.setSelectedSymbol);
  const [userOpen, setUserOpen] = useState(false);
  const [logoutOpen, setLogoutOpen] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);

  const { data: positions } = useQuery({
    queryKey: ["positions"],
    queryFn: tradingService.listPositions,
    staleTime: 0,
    refetchInterval: 2_000,
    refetchOnWindowFocus: true,
  });
  const positionCount = positions?.length ?? 0;
  const totalCost = positions?.reduce(
    (sum, position) => sum + Number(position.volume) * Number(position.avg_cost),
    0
  ) ?? 0;

  useEffect(() => {
    const closeMenu = (event: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(event.target as Node)) {
        setUserOpen(false);
      }
    };
    document.addEventListener("mousedown", closeMenu);
    return () => document.removeEventListener("mousedown", closeMenu);
  }, []);

  const handleSearchSelect = (stock: StockSearchResult) => {
    setSelectedSymbol(stock.symbol);
    router.push(`/market?symbol=${stock.symbol}`);
  };

  const handleLogout = () => {
    logout();
    setLogoutOpen(false);
    toast.success("已退出登录");
    router.replace("/login");
  };

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center gap-3 border-b bg-card px-3 md:gap-5 md:px-5">
      <Link
        href={selectedSymbol ? `/market?symbol=${selectedSymbol}` : "/market"}
        className="flex shrink-0 items-center gap-2"
        aria-label="Quant Platform 行情首页"
      >
        <svg className="h-7 w-7 fill-foreground" viewBox="0 0 28 28" aria-hidden="true">
          <rect x="4" y="7" width="15" height="6" rx="3" transform="rotate(-35 4 7)" />
          <rect x="10" y="16" width="15" height="6" rx="3" transform="rotate(-35 10 16)" />
        </svg>
        <span className="hidden text-sm font-semibold sm:inline">Quant</span>
      </Link>

      <StockSearch onSelect={handleSearchSelect} className="max-w-lg flex-1" />
      <div className="flex-1" />

      <Link
        href={selectedSymbol ? `/market?symbol=${selectedSymbol}&panel=trading` : "/market?panel=trading"}
        className="hidden items-center gap-3 rounded-full bg-muted px-3 py-2 text-xs transition-colors hover:bg-accent md:flex"
      >
        <Wallet className="h-4 w-4 text-muted-foreground" />
        <span className="text-muted-foreground">持仓</span>
        <span className="font-semibold tabular-nums">{positionCount}</span>
        <span className="h-3 w-px bg-border" />
        <span className="text-muted-foreground">成本</span>
        <span className="font-semibold tabular-nums">{formatMoney(totalCost)}</span>
      </Link>

      <div ref={userRef} className="relative">
        <button
          type="button"
          onClick={() => setUserOpen((value) => !value)}
          className="flex h-9 items-center gap-2 rounded-full border bg-card px-1.5 pr-2.5 transition-colors hover:bg-muted"
          aria-expanded={userOpen}
        >
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-foreground text-background">
            <User className="h-3.5 w-3.5" />
          </span>
          <span className="hidden max-w-24 truncate text-xs font-medium sm:inline">{user?.nickname ?? "用户"}</span>
          <ChevronDown className={cn("h-3 w-3 text-muted-foreground transition-transform", userOpen && "rotate-180")} />
        </button>

        {userOpen && (
          <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border bg-popover p-1.5 shadow-lg">
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.nickname}</p>
              <p className="mt-0.5 truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <div className="my-1 h-px bg-border" />
            <button
              type="button"
              onClick={() => {
                setUserOpen(false);
                setLogoutOpen(true);
              }}
              className="flex w-full items-center rounded-md px-3 py-2 text-sm text-danger transition-colors hover:bg-muted"
            >
              <LogOut className="mr-2 h-4 w-4" />
              退出登录
            </button>
          </div>
        )}
      </div>

      <AlertDialog open={logoutOpen} onOpenChange={setLogoutOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>确认退出登录？</AlertDialogTitle>
            <AlertDialogDescription>本机保存的当前选股与账号查询缓存也会一并清除。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleLogout}>确认退出</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
