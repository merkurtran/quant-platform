"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import {
  TrendingUp,
  LogOut,
  User,
  ChevronDown,
  Wallet,
} from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { useMarketStore } from "@/stores/market";
import { tradingService } from "@/services/trading";
import { StockSearch } from "@/components/stock-search";
import { toast } from "sonner";
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
import { formatMoney } from "@/lib/format";
import type { StockSearchResult } from "@/types";

export function Navbar() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
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
  const totalCost =
    positions?.reduce(
      (sum, p) => sum + parseFloat(p.volume) * parseFloat(p.avg_cost),
      0
    ) ?? 0;

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleSearchSelect = (stock: StockSearchResult) => {
    setSelectedSymbol(stock.symbol);
    router.push(`/market?symbol=${stock.symbol}`);
  };

  const handleLogout = () => {
    logout();
    setLogoutOpen(false);
    toast.success("已退出登录");
    router.push("/login");
  };

  return (
    <header className="sticky top-0 z-30 flex h-12 items-center gap-4 bg-card px-4">
      {/* Logo */}
      <Link
        href={selectedSymbol ? `/market?symbol=${selectedSymbol}` : "/market"}
        className="flex shrink-0 items-center gap-2"
      >
        <TrendingUp className="h-5 w-5 text-primary" />
        <span className="text-base font-bold">Quant</span>
      </Link>

      {/* 搜索框 */}
      <StockSearch
        onSelect={handleSearchSelect}
        className="max-w-md flex-1"
      />

      <div className="flex-1" />

      {/* 持仓数据 */}
      <Link
        href={
          selectedSymbol
            ? `/market?symbol=${selectedSymbol}&panel=trading`
            : "/market?panel=trading"
        }
        className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm transition-colors hover:bg-accent"
      >
        <Wallet className="h-4 w-4 text-muted-foreground" />
        <span className="text-muted-foreground">持仓</span>
        <span className="font-semibold tabular-nums">{positionCount}</span>
      </Link>
      <div className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm">
        <span className="text-muted-foreground">成本</span>
        <span className="font-semibold tabular-nums">
          {formatMoney(totalCost)}
        </span>
      </div>

      {/* User menu */}
      <div ref={userRef} className="relative">
        <button
          onClick={() => setUserOpen((v) => !v)}
          className="flex items-center gap-2 rounded-md px-2 py-1 transition-colors hover:bg-accent"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-medium">
            {user?.nickname ?? "用户"}
          </span>
          <ChevronDown
            className={cn(
              "h-3 w-3 transition-transform",
              userOpen && "rotate-180"
            )}
          />
        </button>
        {userOpen && (
          <div className="absolute right-0 top-full mt-1 w-48 rounded-lg bg-popover p-1 shadow-md">
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.nickname}</p>
              <p className="truncate text-xs text-muted-foreground">
                {user?.email}
              </p>
            </div>
            <div className="my-1 h-px bg-border/50" />
            <button
              onClick={() => {
                setUserOpen(false);
                setLogoutOpen(true);
              }}
              className="flex w-full items-center rounded-md px-3 py-1.5 text-sm text-danger transition-colors hover:bg-accent"
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
            <AlertDialogDescription>
              退出后需要重新登录才能使用平台功能。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={handleLogout}>
              确认退出
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </header>
  );
}
