import { Navbar } from "@/components/layout/navbar";
import { RightNav } from "@/components/layout/right-nav";
import { AuthGuard } from "@/components/layout/auth-guard";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <AuthGuard>
      <div className="flex h-screen flex-col bg-background">
        <Navbar />
        <div className="flex flex-1 overflow-hidden">
          <main className="flex-1 overflow-hidden">{children}</main>
          <RightNav />
        </div>
      </div>
    </AuthGuard>
  );
}
