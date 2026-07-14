"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Loader2, Play } from "lucide-react";
import Link from "next/link";
import { strategyService } from "@/services/strategies";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { StrategyCopilot } from "@/components/panels/strategy-copilot";
import { STRATEGY_STATUS_LABELS } from "@/constants";
import { toast } from "sonner";

export default function StrategyDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const queryClient = useQueryClient();
  const strategyId = parseInt(params.id);
  const isNew = params.id === "new";

  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [code, setCode] = useState("");
  const [paramsJson, setParamsJson] = useState("{}");

  const { data: strategy, isLoading } = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId),
    enabled: !isNew,
  });

  const initRef = useRef<number | null>(null);
  useEffect(() => {
    if (strategy && initRef.current !== strategy.id) {
      initRef.current = strategy.id;
      setName(strategy.name);
      setDescription(strategy.description ?? "");
      setCode(strategy.code);
      setParamsJson(JSON.stringify(strategy.params, null, 2));
    }
  }, [strategy]);

  const saveMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        name,
        description: description || undefined,
        code,
        params: JSON.parse(paramsJson),
      };
      return isNew
        ? strategyService.create(payload)
        : strategyService.update(strategyId, payload);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      queryClient.invalidateQueries({ queryKey: ["strategy", strategyId] });
      toast.success(isNew ? "创建成功" : "保存成功");
      if (isNew) router.push(`/strategies/${data.id}`);
    },
    onError: () => toast.error("参数 JSON 格式错误"),
  });

  const isArchived = !isNew && strategy?.status === "archived";

  if (!isNew && isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-full space-y-5 overflow-y-auto p-6">
      <div className="flex items-center gap-4">
        <Link href="/strategies" title="返回策略列表">
          <ArrowLeft className="h-5 w-5 text-muted-foreground hover:text-foreground" />
        </Link>
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-xl font-semibold">
            {isNew ? "新建策略" : "编辑策略"}
          </h1>
          {!isNew && strategy && (
            <p className="mt-0.5 truncate text-xs text-muted-foreground">
              {strategy.name}
            </p>
          )}
        </div>
        {!isNew && strategy && (
          <>
            <Badge variant="secondary">
              {STRATEGY_STATUS_LABELS[strategy.status] ?? strategy.status}
            </Badge>
            <Button variant="outline" size="sm" asChild>
              <Link href={`/strategies/${strategyId}/backtest`}>
                <Play className="h-4 w-4" />
                回测
              </Link>
            </Button>
          </>
        )}
      </div>

      <div className="grid items-start gap-4 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card>
          <CardContent className="space-y-4 p-6">
          {isArchived && (
            <div className="rounded border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
              该策略已归档，不可编辑。
            </div>
          )}

          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="name">策略名称 *</Label>
              <Input
                id="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="如：双均线策略"
                disabled={isArchived}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="description">描述</Label>
              <Input
                id="description"
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="可选"
                disabled={isArchived}
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="code">策略代码（backtrader）*</Label>
            <Textarea
              id="code"
              value={code}
              onChange={(event) => setCode(event.target.value)}
              className="min-h-[360px] font-mono text-xs"
              placeholder="import backtrader as bt&#10;..."
              disabled={isArchived}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="params">默认参数（JSON）</Label>
            <Textarea
              id="params"
              value={paramsJson}
              onChange={(event) => setParamsJson(event.target.value)}
              className="min-h-24 font-mono text-xs"
              disabled={isArchived}
            />
          </div>

          <div className="flex justify-end">
            <Button
              onClick={() => saveMutation.mutate()}
              disabled={isArchived || saveMutation.isPending || !name || !code}
            >
              {saveMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {isNew ? "创建策略" : "保存更改"}
            </Button>
          </div>
          </CardContent>
        </Card>

        <StrategyCopilot
          currentName={name}
          disabled={isArchived}
          onApply={(draft) => {
            setName(draft.name);
            setDescription(draft.description);
            setCode(draft.code);
            setParamsJson(JSON.stringify(draft.params, null, 2));
            toast.success("AI 草稿已应用，请检查后保存");
          }}
        />
      </div>
    </div>
  );
}
