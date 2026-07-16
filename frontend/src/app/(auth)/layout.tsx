import Link from "next/link";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <main className="relative min-h-svh overflow-hidden bg-white text-[#090909]">
      <div className="absolute left-[10%] top-[10%] h-[80%] w-[80%] overflow-hidden md:inset-0 md:h-full md:w-full">
        <video
          className="h-full w-full object-cover"
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260508_215831_c6a8989c-d716-4d8d-8745-e972a2eec711.mp4"
          autoPlay
          muted
          loop
          playsInline
          aria-hidden="true"
        />
      </div>

      <div className="absolute inset-0 bg-[linear-gradient(to_top,rgba(255,255,255,0.96)_0%,rgba(255,255,255,0.32)_58%,rgba(255,255,255,0.08)_100%)] md:bg-[linear-gradient(to_right,rgba(255,255,255,0.18)_0%,rgba(255,255,255,0.62)_52%,rgba(255,255,255,0.98)_76%)]" />

      <nav className="fixed inset-x-0 top-0 z-20 flex items-center justify-between p-4 md:px-8 md:py-6">
        <Link href="/" className="flex items-center gap-2 text-sm font-semibold">
          <svg className="h-7 w-7 fill-current" viewBox="0 0 28 28" aria-hidden="true">
            <rect x="4" y="7" width="15" height="6" rx="3" transform="rotate(-35 4 7)" />
            <rect x="10" y="16" width="15" height="6" rx="3" transform="rotate(-35 10 16)" />
          </svg>
          <span className="hidden sm:inline">Quant Platform</span>
        </Link>
        <Link href="/" className="rounded-full bg-[#f4f4f6] px-4 py-2 text-xs font-medium transition-colors hover:bg-[#e9e9ec]">
          返回首页
        </Link>
      </nav>

      <div className="relative z-10 grid min-h-svh items-end px-4 pb-5 pt-24 md:grid-cols-[minmax(0,1fr)_420px] md:items-center md:px-8 md:pb-8">
        <div className="hidden self-end pb-6 md:block">
          <p className="flex items-center gap-2 text-xs text-black/55">
            <span className="h-2 w-2 rounded-full bg-black" />
            真实约束下的策略研究与模拟交易
          </p>
          <h1 className="mt-5 max-w-2xl text-5xl font-light leading-none">
            从一只股票开始，<br />完成一次可信决策。
          </h1>
        </div>

        <div className="w-full rounded-lg border border-black/10 bg-white/95 p-6 shadow-[0_20px_70px_rgba(0,0,0,0.10)] backdrop-blur-sm sm:p-8">
          {children}
        </div>
      </div>
    </main>
  );
}
