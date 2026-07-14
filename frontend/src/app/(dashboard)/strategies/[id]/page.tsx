"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Play, Save } from "lucide-react";
import { strategyService } from "@/services/strategies";
import { StrategyEditorWorkspace } from "@/components/strategy/strategy-editor-workspace";
import { StrategySettingsPanel } from "@/components/strategy/strategy-settings-panel";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { STRATEGY_STATUS_LABELS } from "@/constants";
import type { StrategyDraft } from "@/types";
import { toast } from "sonner";

export default function StrategyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const strategyId = Number(params.id);
  const isNew = params.id === "new";
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState("");
  const [paramsJson, setParamsJson] = useState("{}");

  const strategyQuery = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId),
    enabled: !isNew,
  });

  const initRef = useRef<number | null>(null);
  useEffect(() => {
    const strategy = strategyQuery.data;
    if (strategy && initRef.current !== strategy.id) {
      initRef.current = strategy.id;
      setName(strategy.name);
      setDescription(strategy.description ?? "");
      setCode(strategy.code);
      setParamsJson(JSON.stringify(strategy.params, null, 2));
    }
  }, [strategyQuery.data]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      let parsedParams: Record<string, unknown>;
      try {
        parsedParams = JSON.parse(paramsJson) as Record<string, unknown>;
      } catch {
        throw new Error("INVALID_PARAMS_JSON");
      }
      const payload = {
        name,
        description: description || undefined,
        code,
        params: parsedParams,
      };
      return isNew
        ? strategyService.create(payload)
        : strategyService.update(strategyId, payload);
    },
    onSuccess: (savedStrategy) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", strategyId] });
      toast.success(isNew ? "策略已创建" : "策略已保存");
      if (isNew) router.push(`/strategies/${savedStrategy.id}`);
    },
    onError: (error) => {
      if (error instanceof Error && error.message === "INVALID_PARAMS_JSON") {
        toast.error("策略参数必须是有效的 JSON 对象");
      }
    },
  });

  const applyDraft = (draft: StrategyDraft) => {
    setName(draft.name);
    setDescription(draft.description);
    setCode(draft.code);
    setParamsJson(JSON.stringify(draft.params, null, 2));
    toast.success("AI 草稿已应用，请检查后保存");
  };

  if (!isNew && strategyQuery.isLoading) {
    return (
      <div className="h-full space-y-4 p-4">
        <div className="h-16 animate-pulse rounded-lg bg-card" />
        <div className="h-[calc(100%_-_5rem)] animate-pulse rounded-lg bg-card" />
      </div>
    );
  }

  if (!isNew && strategyQuery.isError) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3">
        <p className="text-sm text-muted-foreground">策略加载失败</p>
        <Button variant="outline" onClick={() => strategyQuery.refetch()}>重试</Button>
      </div>
    );
  }

  const strategy = strategyQuery.data;
  const isArchived = !isNew && strategy?.status === "archived";

  return (
    <div className="flex h-full flex-col overflow-y-auto xl:overflow-hidden">
      <header className="flex shrink-0 items-center gap-3 bg-card px-6 py-4">
        <Button variant="ghost" size="icon" asChild>
          <Link href="/strategies" title="返回策略列表">
            <ArrowLeft className="h-4 w-4" />
          </Link>
        </Button>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">
            {isNew ? "新建策略" : name || "未命名策略"}
          </h1>
          <p className="text-xs text-muted-foreground">策略编辑工作台</p>
        </div>
        {!isNew && strategy && (
          <Badge variant={isArchived ? "warning" : "secondary"}>
            {STRATEGY_STATUS_LABELS[strategy.status] ?? strategy.status}
          </Badge>
        )}
        {!isNew && (
          <Button variant="outline" asChild>
            <Link href={`/market?panel=backtest&strategyId=${strategyId}`}>
              <Play className="h-4 w-4" />
              回测
            </Link>
          </Button>
        )}
        <Button
          onClick={() => saveMutation.mutate()}
          disabled={isArchived || saveMutation.isPending || !name.trim() || !code.trim()}
        >
          <Save className="h-4 w-4" />
          {saveMutation.isPending ? "保存中" : isNew ? "创建策略" : "保存"}
        </Button>
      </header>

      {isArchived && (
        <div className="mx-4 mt-4 rounded-lg bg-warning/10 px-4 py-3 text-sm text-warning">
          该策略已归档，只能查看，不能继续编辑。
        </div>
      )}

      <main className="grid flex-1 items-start gap-4 p-4 xl:min-h-0 xl:grid-cols-[minmax(0,1fr)_360px] xl:overflow-hidden">
        <StrategyEditorWorkspace
          name={name}
          description={description}
          code={code}
          disabled={isArchived}
          onNameChange={setName}
          onDescriptionChange={setDescription}
          onCodeChange={setCode}
        />
        <StrategySettingsPanel
          currentName={name}
          paramsJson={paramsJson}
          disabled={isArchived}
          onParamsChange={setParamsJson}
          onApplyDraft={applyDraft}
        />
      </main>
    </div>
  );
}
