import { Braces } from "lucide-react";
import { StrategyCopilot } from "@/components/panels/strategy-copilot";
import { Textarea } from "@/components/ui/textarea";
import type { StrategyDraft } from "@/types";

interface StrategySettingsPanelProps {
  currentName: string;
  paramsJson: string;
  disabled?: boolean;
  onParamsChange: (value: string) => void;
  onApplyDraft: (draft: StrategyDraft) => void;
}

export function StrategySettingsPanel({
  currentName,
  paramsJson,
  disabled = false,
  onParamsChange,
  onApplyDraft,
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
        <Textarea
          id="params"
          value={paramsJson}
          onChange={(event) => onParamsChange(event.target.value)}
          className="min-h-44 resize-y bg-muted/30 font-mono text-xs leading-5 tabular-nums"
          spellCheck={false}
          disabled={disabled}
        />
      </section>

      <StrategyCopilot
        currentName={currentName}
        disabled={disabled}
        onApply={onApplyDraft}
      />
    </aside>
  );
}
