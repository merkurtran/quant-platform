"use client";

import { Input } from "@/components/ui/input";
import {
  parameterMeta,
  type StrategyParameterField,
} from "@/lib/strategy-parameters";

interface StrategyParameterEditorProps {
  fields: StrategyParameterField[];
  disabled?: boolean;
  onChange: (fields: StrategyParameterField[]) => void;
}

export function StrategyParameterEditor({
  fields,
  disabled = false,
  onChange,
}: StrategyParameterEditorProps) {
  const updateValue = (id: string, value: string) => {
    onChange(
      fields.map((field) =>
        field.id === id
          ? {
              ...field,
              value,
              valueKind: undefined,
            }
          : field
      )
    );
  };

  return (
    <div className="space-y-3">
      {fields.length > 0 ? (
        <div className="space-y-2">
          {fields.map((field) => {
            const meta = parameterMeta(field.name);
            return (
              <div key={field.id} className="rounded bg-muted/40 p-3">
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <span className="text-xs font-medium">{meta.label}</span>
                  <code className="text-[10px] text-muted-foreground">{field.name}</code>
                </div>
                <p className="mb-2 text-[10px] leading-4 text-muted-foreground">
                  {field.description ?? meta.description}
                </p>
                <Input
                  value={field.value}
                  onChange={(event) => updateValue(field.id, event.target.value)}
                  aria-label={`${meta.label} ${field.name}`}
                  className="h-9 text-xs tabular-nums"
                  disabled={disabled}
                />
              </div>
            );
          })}
        </div>
      ) : (
        <p className="rounded-lg bg-muted/30 px-3 py-4 text-center text-xs text-muted-foreground">
          当前策略没有可调参数，参数需在策略代码中定义。
        </p>
      )}
    </div>
  );
}
