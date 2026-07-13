"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState, useRef, useEffect } from "react";
import {
  CandlestickChart,
  Code2,
  ArrowLeftRight,
  Bell,
  Bot,
  TrendingUp,
  LogOut,
  User,
  ChevronDown,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/stores/auth";
import { toast } from "sonner";

const NAV = [
  { href: "/market", label: "行情", icon: CandlestickChart },
  { href: "/strategies", label: "策略", icon: Code2 },
  { href: "/trading/orders", label: "交易", icon: ArrowLeftRight },
  { href: "/alerts", label: "告警", icon: Bell },
  { href: "/ai", label: "AI 助手", icon: Bot },
];

const TRADING_SUB = [
  { href: "/trading/orders", label: "订单" },
  { href: "/trading/positions", label: "持仓" },
  { href: "/trading/accounts", label: "账户" },
];

export function Navbar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [tradingOpen, setTradingOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const tradingRef = useRef<HTMLDivElement>(null);
  const userRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (tradingRef.current && !tradingRef.current.contains(e.target as Node)) {
        setTradingOpen(false);
      }
      if (userRef.current && !userRef.current.contains(e.target as Node)) {
        setUserOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleLogout = () => {
    logout();
    toast.success("已退出登录");
    router.push("/login");
  };

  const isTradingActive = pathname.startsWith("/trading");

  return (
    <header className="sticky top-0 z-30 flex h-12 items-center border-b border-border bg-background/95 px-4 backdrop-blur">
      {/* Logo */}
      <Link href="/market" className="mr-6 flex items-center gap-2">
        <TrendingUp className="h-5 w-5 text-primary" />
        <span className="text-base font-bold">Quant</span>
      </Link>

      {/* Nav */}
      <nav className="flex items-center gap-0.5">
        {NAV.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
          const isTrading = item.href === "/trading/orders";

          if (isTrading) {
            return (
              <div key={item.label} ref={tradingRef} className="relative">
                <button
                  onClick={() => setTradingOpen((v) => !v)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                    isTradingActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                  <ChevronDown className={cn("h-3 w-3 transition-transform", tradingOpen && "rotate-180")} />
                </button>
                {tradingOpen && (
                  <div className="absolute left-0 top-full mt-1 w-32 rounded-lg border border-border bg-popover p-1 shadow-md">
                    {TRADING_SUB.map((sub) => (
                      <Link
                        key={sub.href}
                        href={sub.href}
                        onClick={() => setTradingOpen(false)}
                        className={cn(
                          "block rounded-md px-3 py-1.5 text-sm transition-colors",
                          pathname === sub.href
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                        )}
                      >
                        {sub.label}
                      </Link>
                    ))}
                  </div>
                )}
              </div>
            );
          }

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-secondary hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="flex-1" />

      {/* User menu */}
      <div ref={userRef} className="relative">
        <button
          onClick={() => setUserOpen((v) => !v)}
          className="flex items-center gap-2 rounded-md px-2 py-1 transition-colors hover:bg-secondary"
        >
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/10">
            <User className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-medium">{user?.nickname ?? "用户"}</span>
          <ChevronDown className={cn("h-3 w-3 transition-transform", userOpen && "rotate-180")} />
        </button>
        {userOpen && (
          <div className="absolute right-0 top-full mt-1 w-48 rounded-lg border border-border bg-popover p-1 shadow-md">
            <div className="px-3 py-2">
              <p className="text-sm font-medium">{user?.nickname}</p>
              <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
            </div>
            <div className="my-1 h-px bg-border" />
            <button
              onClick={handleLogout}
              className="flex w-full items-center rounded-md px-3 py-1.5 text-sm text-danger transition-colors hover:bg-secondary"
            >
              <LogOut className="mr-2 h-4 w-4" />
              退出登录
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
