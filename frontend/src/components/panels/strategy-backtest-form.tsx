import { Loader2, Play, Settings2 } from "lucide-react";
import { BacktestField, BacktestStatus } from "@/components/panels/strategy-backtest-states";
import { StrategyParameterEditor } from "@/components/strategy/strategy-parameter-editor";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { Strategy } from "@/types";
import type { StrategyParameterField } from "@/lib/strategy-parameters";

interface StrategyBacktestFormProps {
  strategies: Strategy[];
  strategyId: number | null;
  startDate: string;
  endDate: string;
  symbol: string;
  capital: string;
  commissionRate: string;
  slippageRate: string;
  isRunning: boolean;
  canStart: boolean;
  parameterFields: StrategyParameterField[];
  status?: string;
  errorMessage?: string | null;
  onStrategyChange: (value: string) => void;
  onStartDateChange: (value: string) => void;
  onEndDateChange: (value: string) => void;
  onSymbolChange: (value: string) => void;
  onCapitalChange: (value: string) => void;
  onCommissionRateChange: (value: string) => void;
  onSlippageRateChange: (value: string) => void;
  onParametersChange: (fields: StrategyParameterField[]) => void;
  onStart: () => void;
}

export function StrategyBacktestForm(props: StrategyBacktestFormProps) {
  return (
    <>
      <div className="space-y-1.5">
        <Label className="text-xs">策略</Label>
        <Select value={props.strategyId?.toString()} onValueChange={props.onStrategyChange}>
          <SelectTrigger className="h-8 text-xs"><SelectValue /></SelectTrigger>
          <SelectContent>
            {props.strategies.map((strategy) => (
              <SelectItem key={strategy.id} value={strategy.id.toString()}>{strategy.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <BacktestField label="开始日期" type="date" value={props.startDate} onChange={props.onStartDateChange} />
        <BacktestField label="结束日期" type="date" value={props.endDate} onChange={props.onEndDateChange} />
      </div>
      <BacktestField label="回测标的" value={props.symbol} onChange={props.onSymbolChange} />
      <BacktestField label="初始资金" value={props.capital} onChange={props.onCapitalChange} />

      <section className="space-y-2 border-y border-border/70 py-3">
        <div className="flex items-center gap-2">
          <Settings2 className="h-3.5 w-3.5 text-primary" />
          <div>
            <Label className="text-xs">回测环境</Label>
            <p className="text-[10px] text-muted-foreground">每次回测单独保存，历史结果可追溯</p>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <BacktestField
            label="手续费率"
            description="0.001 = 0.1%"
            type="number"
            step="0.0001"
            min="0"
            value={props.commissionRate}
            onChange={props.onCommissionRateChange}
          />
          <BacktestField
            label="滑点率"
            description="0.0005 = 0.05%"
            type="number"
            step="0.0001"
            min="0"
            value={props.slippageRate}
            onChange={props.onSlippageRateChange}
          />
        </div>
      </section>

      {props.parameterFields.length > 0 && (
        <div className="space-y-2 pt-1">
          <div className="flex items-center justify-between gap-2">
            <div>
              <Label className="text-xs">策略参数</Label>
              <p className="text-[10px] text-muted-foreground">由当前策略代码定义</p>
            </div>
            <span className="text-[10px] tabular-nums text-muted-foreground">
              {props.parameterFields.length} 项
            </span>
          </div>
          <StrategyParameterEditor
            fields={props.parameterFields}
            disabled={props.isRunning}
            onChange={props.onParametersChange}
          />
        </div>
      )}

      <Button className="w-full" size="sm" onClick={props.onStart} disabled={props.isRunning || !props.canStart}>
        {props.isRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
        {props.isRunning ? "回测运行中" : "开始回测"}
      </Button>

      <BacktestStatus status={props.status} errorMessage={props.errorMessage} />
    </>
  );
}
