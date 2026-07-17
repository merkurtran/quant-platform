import { Braces } from "lucide-react";
import { StrategyCopilot } from "@/components/panels/strategy-copilot";
import { BacktestHistory } from "@/components/panels/backtest-history";
import { StrategyParameterEditor } from "@/components/strategy/strategy-parameter-editor";
import type { StrategyParameterField } from "@/lib/strategy-parameters";
import type { BacktestRunSummary, StrategyDraft } from "@/types";

interface StrategySettingsPanelProps {
  currentName: string;
  parameterFields: StrategyParameterField[];
  history?: BacktestRunSummary[];
  historyLoading?: boolean;
  disabled?: boolean;
  onParametersChange: (fields: StrategyParameterField[]) => void;
  onApplyDraft: (draft: StrategyDraft) => void;
  onHistorySelect: (run: BacktestRunSummary) => void;
}

export function StrategySettingsPanel({
  currentName,
  parameterFields,
  history,
  historyLoading = false,
  disabled = false,
  onParametersChange,
  onApplyDraft,
  onHistorySelect,
}: StrategySettingsPanelProps) {
  return (
    <aside className="overflow-hidden rounded-lg bg-card xl:h-full xl:overflow-y-auto">
      <section className="p-4">
        <div className="mb-3 flex items-center gap-2">
          <Braces className="h-4 w-4 text-primary" />
          <div>
            <h2 className="text-sm font-semibold">策略参数</h2>
            <p className="text-xs text-muted-foreground">回测时可覆盖这些默认值</p>
          </div>
        </div>
        <StrategyParameterEditor
          fields={parameterFields}
          disabled={disabled}
          onChange={onParametersChange}
        />
      </section>

      {history && (
        <section className="border-t border-border/70 px-4 pb-4 pt-2">
          <BacktestHistory
            runs={history}
            activeRunId={null}
            isLoading={historyLoading}
            onSelect={onHistorySelect}
          />
        </section>
      )}

      <StrategyCopilot
        currentName={currentName}
        disabled={disabled}
        onApply={onApplyDraft}
      />
    </aside>
  );
}
