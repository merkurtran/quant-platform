"use client";

import { Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  createParameterField,
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
  const updateField = (
    id: string,
    key: "name" | "value",
    value: string
  ) => {
    onChange(
      fields.map((field) =>
        field.id === id
          ? {
              ...field,
              [key]: value,
              valueKind: key === "value" ? undefined : field.valueKind,
            }
          : field
      )
    );
  };

  return (
    <div className="space-y-3">
      {fields.length > 0 ? (
        <div className="space-y-2">
          <div className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_32px] gap-2 px-1 text-xs text-muted-foreground">
            <span>参数名</span>
            <span>默认值</span>
            <span className="sr-only">操作</span>
          </div>
          {fields.map((field) => (
            <div
              key={field.id}
              className="grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)_32px] items-center gap-2"
            >
              <Input
                value={field.name}
                onChange={(event) => updateField(field.id, "name", event.target.value)}
                placeholder="如 fast_period"
                className="h-9 text-xs"
                disabled={disabled}
              />
              <Input
                value={field.value}
                onChange={(event) => updateField(field.id, "value", event.target.value)}
                placeholder="如 20"
                className="h-9 text-xs tabular-nums"
                disabled={disabled}
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-8 w-8 text-muted-foreground hover:text-danger"
                title={`删除参数 ${field.name || "未命名"}`}
                onClick={() => onChange(fields.filter((item) => item.id !== field.id))}
                disabled={disabled}
              >
                <Trash2 className="h-4 w-4" />
                <span className="sr-only">删除参数</span>
              </Button>
            </div>
          ))}
        </div>
      ) : (
        <p className="rounded-lg bg-muted/30 px-3 py-4 text-center text-xs text-muted-foreground">
          暂无参数，需要时可直接添加。
        </p>
      )}

      <Button
        type="button"
        size="sm"
        variant="outline"
        className="w-full"
        onClick={() => onChange([...fields, createParameterField()])}
        disabled={disabled}
      >
        <Plus className="h-4 w-4" />
        添加参数
      </Button>
    </div>
  );
}
