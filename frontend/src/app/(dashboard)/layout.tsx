import { Navbar } from "@/components/layout/navbar";
import { RightNav } from "@/components/layout/right-nav";
import { AuthGuard } from "@/components/layout/auth-guard";
import { MarketSocketProvider } from "@/components/layout/market-socket-provider";
import { GlobalLoadingIndicator } from "@/components/layout/global-loading-indicator";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <MarketSocketProvider>
        <div className="flex h-screen flex-col gap-px bg-border/70">
          <GlobalLoadingIndicator />
          <Navbar />
          <div className="flex min-h-0 flex-1 gap-px overflow-hidden">
            <main className="flex-1 overflow-hidden bg-background">{children}</main>
            <RightNav />
          </div>
        </div>
      </MarketSocketProvider>
    </AuthGuard>
  );
}
