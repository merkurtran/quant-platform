"use client";
import type { BacktestResultViewModel } from "@/components/panels/backtest-result";
import { BacktestEmptyState, BacktestPanelHeader } from "@/components/panels/strategy-backtest-states";
import { BacktestHistory } from "@/components/panels/backtest-history";
import { StrategyBacktestForm } from "@/components/panels/strategy-backtest-form";
import { useStrategyBacktestPanel } from "@/hooks/use-strategy-backtest-panel";

interface StrategyBacktestPanelProps {
  symbol: string | null;
  onResultChange?: (result: BacktestResultViewModel | null) => void;
}

export function StrategyBacktestPanel({ symbol, onResultChange }: StrategyBacktestPanelProps) {
  const panel = useStrategyBacktestPanel(symbol, onResultChange);

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <BacktestPanelHeader strategyId={panel.strategyId} />
      <div className="flex-1 space-y-4 overflow-y-auto border-t border-border/70 p-3">
        {panel.isLoading ? (
          <div className="space-y-3">
            <div className="h-9 animate-pulse rounded bg-muted" />
            <div className="h-32 animate-pulse rounded bg-muted" />
          </div>
        ) : !panel.strategies?.length ? (
          <BacktestEmptyState />
        ) : (
          <>
            <StrategyBacktestForm
              strategies={panel.strategies}
              strategyId={panel.strategyId}
              startDate={panel.startDate}
              endDate={panel.endDate}
              symbol={panel.backtestSymbol}
              capital={panel.capital}
              commissionRate={panel.commissionRate}
              slippageRate={panel.slippageRate}
              isRunning={panel.isRunning}
              canStart={Boolean(panel.strategy && panel.backtestSymbol && panel.startDate && panel.endDate)}
              parameterFields={panel.parameterFields}
              status={panel.result?.status}
              errorMessage={panel.result?.error_message}
              onStrategyChange={panel.selectStrategy}
              onStartDateChange={panel.setStartDate}
              onEndDateChange={panel.setEndDate}
              onSymbolChange={panel.setBacktestSymbol}
              onCapitalChange={panel.setCapital}
              onCommissionRateChange={panel.setCommissionRate}
              onSlippageRateChange={panel.setSlippageRate}
              onParametersChange={panel.setParameterFields}
              onStart={panel.handleStart}
            />
            <BacktestHistory
              runs={panel.history}
              activeRunId={panel.activeRunId}
              isLoading={panel.historyLoading}
              onSelect={panel.selectHistory}
            />
          </>
        )}
      </div>
    </div>
  );
}
