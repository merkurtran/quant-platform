"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  CandlestickChart,
  Code2,
  ArrowLeftRight,
  Bell,
  Sun,
  Moon,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useThemeStore } from "@/stores/theme";
import { useMarketStore } from "@/stores/market";

const NAV_ITEMS = [
  { label: "行情", icon: CandlestickChart, href: "/market", panel: undefined },
  { label: "告警", icon: Bell, href: "/market", panel: "alerts" },
  { label: "策略", icon: Code2, href: "/market", panel: "backtest" },
  { label: "交易", icon: ArrowLeftRight, href: "/market", panel: "trading" },
];

export function RightNav() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const currentPanel = searchParams.get("panel");
  const selectedSymbol = useMarketStore((state) => state.selectedSymbol);
  const { theme, toggleTheme, _hasHydrated } = useThemeStore();

  return (
    <nav className="relative z-40 flex w-12 shrink-0 flex-col items-center bg-card py-3">
      {/* 居中的导航图标 */}
      <div className="flex flex-1 flex-col items-center gap-1">
        {NAV_ITEMS.map((item) => {
          const marketSymbol = searchParams.get("symbol") ?? selectedSymbol;
          const marketParams = new URLSearchParams();
          if (marketSymbol) marketParams.set("symbol", marketSymbol);
          if (item.panel) marketParams.set("panel", item.panel);
          const href =
            item.href === "/market" && marketParams.size > 0
              ? `${item.href}?${marketParams.toString()}`
              : item.href;

          let isActive: boolean;
          if (item.panel) {
            isActive = pathname === item.href && currentPanel === item.panel;
          } else if (item.href === "/market") {
            isActive = pathname === "/market" && !currentPanel;
          } else {
            isActive = pathname.startsWith(item.href);
          }

          const Icon = item.icon;

          return (
            <Link
              key={item.label}
              href={href}
              className={cn(
                "group relative flex h-9 w-9 items-center justify-center rounded-lg transition-colors",
                isActive
                  ? "bg-muted text-primary"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <Icon className="h-5 w-5" strokeWidth={1.5} />
              <span className="pointer-events-none absolute right-full z-50 mr-2 whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs text-foreground opacity-0 shadow-md transition-opacity group-hover:opacity-100">
                {item.label}
              </span>
            </Link>
          );
        })}
      </div>

      {/* 主题切换按钮 — 推到右侧底部 */}
      {_hasHydrated && (
        <button
          onClick={toggleTheme}
          className="group relative mt-auto flex h-9 w-9 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          title="切换主题"
        >
          {theme === "light" ? (
            <Moon className="h-5 w-5" strokeWidth={1.5} />
          ) : (
            <Sun className="h-5 w-5" strokeWidth={1.5} />
          )}
          <span className="pointer-events-none absolute right-full z-50 mr-2 whitespace-nowrap rounded-md bg-popover px-2 py-1 text-xs text-foreground opacity-0 shadow-md transition-opacity group-hover:opacity-100">
            {theme === "light" ? "暗色模式" : "亮色模式"}
          </span>
        </button>
      )}
    </nav>
  );
}
