import { redirect } from "next/navigation";

interface StrategyBacktestRedirectProps {
  params: Promise<{ id: string }>;
}

export default async function StrategyBacktestRedirect({
  params,
}: StrategyBacktestRedirectProps) {
  const { id } = await params;
  redirect(`/market?panel=backtest&strategyId=${id}`);
}
