import { TrendingUp } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-secondary px-4">
      <div className="w-full max-w-md">
        <div className="mb-8 flex items-center justify-center gap-2">
          <TrendingUp className="h-8 w-8 text-primary" />
          <span className="text-2xl font-bold">Quant Platform</span>
        </div>
        {children}
      </div>
    </div>
  );
}
