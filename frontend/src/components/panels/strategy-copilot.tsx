"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Loader2, Sparkles } from "lucide-react";
import { aiService } from "@/services/ai";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { StrategyDraft } from "@/types";

interface StrategyCopilotProps {
  currentName: string;
  disabled?: boolean;
  onApply: (draft: StrategyDraft) => void;
}

export function StrategyCopilot({
  currentName,
  disabled = false,
  onApply,
}: StrategyCopilotProps) {
  const [prompt, setPrompt] = useState("");
  const [draft, setDraft] = useState<StrategyDraft | null>(null);

  const mutation = useMutation({
    mutationFn: () => aiService.generateStrategyDraft(prompt, currentName),
    onSuccess: setDraft,
  });

  return (
    <section className="bg-muted/20 p-4">
      <div className="flex items-center gap-2">
        <Sparkles className="h-4 w-4 text-primary" />
        <div>
          <h2 className="text-sm font-semibold">AI 策略生成</h2>
          <p className="text-xs text-muted-foreground">描述交易逻辑，生成可编辑草稿</p>
        </div>
      </div>

      <div className="mt-3 space-y-3">
        <Textarea
          value={prompt}
          onChange={(event) => setPrompt(event.target.value)}
          className="min-h-32 resize-y bg-card text-xs leading-5"
          placeholder="描述交易逻辑、指标、周期与风控条件"
          disabled={disabled || mutation.isPending}
        />
        <Button
          className="w-full"
          size="sm"
          onClick={() => mutation.mutate()}
          disabled={disabled || mutation.isPending || prompt.trim().length < 5}
        >
          {mutation.isPending ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <Sparkles className="h-4 w-4" />
          )}
          {draft ? "重新生成" : "生成策略草稿"}
        </Button>

        {mutation.isError && (
          <p className="text-xs leading-5 text-danger">
            {mutation.error instanceof Error
              ? mutation.error.message
              : "策略生成失败，请稍后重试"}
          </p>
        )}

        {draft && (
          <div className="space-y-3 rounded-lg bg-card p-3">
            <div>
              <p className="text-[10px] text-muted-foreground">预览</p>
              <p className="mt-1 text-xs font-medium">{draft.name}</p>
              <p className="mt-1 line-clamp-3 text-[11px] leading-4 text-muted-foreground">
                {draft.description}
              </p>
            </div>
            <pre className="max-h-56 overflow-auto rounded-md bg-muted/30 p-2 text-[10px] leading-4">
              {draft.code}
            </pre>
            <Button
              className="w-full"
              size="sm"
              variant="outline"
              onClick={() => onApply(draft)}
              disabled={disabled}
            >
              <Check className="h-4 w-4" />
              应用到编辑器
            </Button>
            <p className="text-[10px] leading-4 text-muted-foreground">
              应用后仍需检查代码并手动保存。
            </p>
          </div>
        )}
      </div>
    </section>
  );
}
