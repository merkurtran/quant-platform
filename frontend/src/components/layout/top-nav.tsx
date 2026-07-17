"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  CandlestickChart,
  Code2,
  ArrowLeftRight,
  Bell,
  Bot,
  TrendingUp,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/market", label: "行情", icon: CandlestickChart },
  { href: "/strategies", label: "策略", icon: Code2 },
  { href: "/trading/orders", label: "交易", icon: ArrowLeftRight },
  { href: "/alerts", label: "告警", icon: Bell },
  { href: "/ai", label: "AI 助手", icon: Bot },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-30 flex h-14 items-center border-b border-border bg-background/80 px-4 backdrop-blur">
      {/* Logo */}
      <Link href="/market" className="flex items-center gap-2 mr-6 shrink-0">
        <TrendingUp className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold">Quant</span>
      </Link>

      {/* 横向导航 */}
      <nav className="flex items-center gap-1">
        {NAV.map((item) => {
          const isActive =
            pathname === item.href || pathname.startsWith(item.href + "/");
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
    </header>
  );
}
