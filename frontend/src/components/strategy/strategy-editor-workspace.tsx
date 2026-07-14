import { FileCode2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

interface StrategyEditorWorkspaceProps {
  name: string;
  description: string;
  code: string;
  disabled?: boolean;
  onNameChange: (value: string) => void;
  onDescriptionChange: (value: string) => void;
  onCodeChange: (value: string) => void;
}

export function StrategyEditorWorkspace({
  name,
  description,
  code,
  disabled = false,
  onNameChange,
  onDescriptionChange,
  onCodeChange,
}: StrategyEditorWorkspaceProps) {
  return (
    <section className="flex min-h-[600px] flex-col overflow-hidden rounded-lg bg-card xl:h-full xl:min-h-0">
      <div className="flex h-10 shrink-0 items-center gap-2 bg-muted/40 px-4">
        <FileCode2 className="h-4 w-4 text-primary" />
        <span className="font-mono text-xs text-muted-foreground">strategy.py</span>
        <div className="ml-auto flex gap-2">
          <Badge variant="secondary" className="font-mono text-[10px]">Python</Badge>
          <Badge variant="default" className="font-mono text-[10px]">backtrader</Badge>
        </div>
      </div>

      <div className="grid shrink-0 gap-4 p-4 md:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor="name">策略名称 *</Label>
          <Input
            id="name"
            value={name}
            onChange={(event) => onNameChange(event.target.value)}
            placeholder="如：双均线交叉策略"
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="description">策略描述</Label>
          <Input
            id="description"
            value={description}
            onChange={(event) => onDescriptionChange(event.target.value)}
            placeholder="简要说明入场、退出和风控逻辑"
            disabled={disabled}
          />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col px-4 pb-4">
        <Label htmlFor="code" className="mb-1.5">策略代码 *</Label>
        <Textarea
          id="code"
          value={code}
          onChange={(event) => onCodeChange(event.target.value)}
          className="min-h-[460px] flex-1 resize-none bg-background font-mono text-xs leading-6 tabular-nums xl:min-h-0"
          placeholder="import backtrader as bt&#10;&#10;class Strategy(bt.Strategy):&#10;    ..."
          spellCheck={false}
          disabled={disabled}
        />
      </div>
    </section>
  );
}
