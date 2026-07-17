"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  CandlestickChart,
  Code2,
  ArrowLeftRight,
  Bell,
  Bot,
  TrendingUp,
  ChevronRight,
} from "lucide-react";
import { cn } from "@/lib/utils";

const NAV = [
  {
    label: "行情",
    icon: CandlestickChart,
    children: [
      { href: "/market", label: "自选股" },
    ],
  },
  {
    label: "策略",
    icon: Code2,
    children: [
      { href: "/strategies", label: "策略列表" },
    ],
  },
  {
    label: "交易",
    icon: ArrowLeftRight,
    children: [
      { href: "/trading/orders", label: "订单" },
      { href: "/trading/positions", label: "持仓" },
      { href: "/trading/accounts", label: "账户" },
    ],
  },
  {
    label: "告警",
    icon: Bell,
    children: [
      { href: "/alerts", label: "规则列表" },
    ],
  },
  {
    label: "AI 助手",
    icon: Bot,
    children: [
      { href: "/ai", label: "对话" },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  // 默认展开所有有当前激活子项的分组
  const [openKeys, setOpenKeys] = useState<Set<string>>(() => {
    const init = new Set<string>();
    NAV.forEach((item) => {
      if (
        item.children.some(
          (c) => pathname === c.href || pathname.startsWith(c.href + "/")
        )
      ) {
        init.add(item.label);
      }
    });
    return init;
  });

  const toggle = (label: string) => {
    setOpenKeys((prev) => {
      const next = new Set(prev);
      if (next.has(label)) {
        next.delete(label);
      } else {
        next.add(label);
      }
      return next;
    });
  };

  return (
    <aside className="fixed left-0 top-0 z-30 flex h-screen w-60 flex-col border-r border-border bg-background">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2 border-b border-border px-6">
        <TrendingUp className="h-6 w-6 text-primary" />
        <span className="text-lg font-bold">Quant</span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto p-3">
        {NAV.map((item) => {
          const isActive = item.children.some(
            (c) => pathname === c.href || pathname.startsWith(c.href + "/")
          );
          const isOpen = openKeys.has(item.label);

          return (
            <div key={item.label} className="mb-1">
              <button
                onClick={() => toggle(item.label)}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary/10 text-primary"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                )}
              >
                <item.icon className="h-4 w-4" />
                <span className="flex-1 text-left">{item.label}</span>
                <ChevronRight
                  className={cn(
                    "h-3.5 w-3.5 transition-transform",
                    isOpen && "rotate-90"
                  )}
                />
              </button>

              {isOpen && (
                <div className="ml-6 mt-1 space-y-0.5 border-l border-border pl-3">
                  {item.children.map((sub) => {
                    const isSubActive = pathname === sub.href;
                    return (
                      <Link
                        key={sub.href}
                        href={sub.href}
                        className={cn(
                          "block rounded-md px-3 py-1.5 text-sm transition-colors",
                          isSubActive
                            ? "text-primary font-medium"
                            : "text-muted-foreground hover:text-foreground"
                        )}
                      >
                        {sub.label}
                      </Link>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
