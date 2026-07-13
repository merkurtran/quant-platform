"use client";

import { useState, useEffect, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Play, Loader2 } from "lucide-react";
import Link from "next/link";
import { strategyService } from "@/services/strategies";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { STRATEGY_STATUS_LABELS, BACKTEST_STATUS_LABELS } from "@/constants";
import { formatPercent } from "@/lib/format";
import { toast } from "sonner";
import type { BacktestRunResult } from "@/types";

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

  // 回测表单
  const [btStart, setBtStart] = useState("");
  const [btEnd, setBtEnd] = useState("");
  const [btCapital, setBtCapital] = useState("1000000");
  const [btSymbols, setBtSymbols] = useState("");
  const [btResult, setBtResult] = useState<BacktestRunResult | null>(null);
  const [btLoading, setBtLoading] = useState(false);
  // 防止组件卸载后 setTimeout/poll 还在跑
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const mountedRef = useRef(true);

  const { data: strategy, isLoading } = useQuery({
    queryKey: ["strategy", strategyId],
    queryFn: () => strategyService.get(strategyId),
    enabled: !isNew,
  });

  useEffect(() => {
    return () => {
      mountedRef.current = false;
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    };
  }, []);

  // 表单初始化
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
      if (isNew) {
        return strategyService.create(payload);
      }
      return strategyService.update(strategyId, payload);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["strategies"] });
      toast.success(isNew ? "创建成功" : "保存成功");
      if (isNew) {
        router.push(`/strategies/${data.id}`);
      }
    },
    onError: () => {
      toast.error("参数 JSON 格式错误");
    },
  });

  const startBacktest = () => {
    if (!btStart || !btEnd || !btSymbols) return;
    setBtResult(null);
    setBtLoading(true);

    const poll = async () => {
      try {
        const result = await strategyService.getBacktestRun(pollRunIdRef.current!);
        if (!mountedRef.current) return;
        setBtResult(result);
        if (result.status === "running" || result.status === "queued") {
          // 限制最大轮询次数和超时（避免无限循环）
          pollCountRef.current++;
          if (pollCountRef.current > 150) {  // 150 * 2s = 5 分钟超时
            setBtLoading(false);
            toast.error("回测超时，请稍后手动查询");
            return;
          }
          pollTimerRef.current = setTimeout(poll, 2000);
        } else {
          setBtLoading(false);
          if (result.status === "success") {
            toast.success("回测完成");
          } else if (result.status === "failed") {
            toast.error("回测失败: " + (result.error_message ?? "未知错误"));
          } else {
            toast.warning("回测状态未知: " + result.status);
          }
        }
      } catch {
        if (mountedRef.current) {
          setBtLoading(false);
          toast.error("查询回测结果失败");
        }
      }
    };

    strategyService
      .startBacktest(strategyId, {
        start_date: btStart,
        end_date: btEnd,
        initial_capital: btCapital,
        symbols: btSymbols.split(",").map((s) => s.trim()),
        params: JSON.parse(paramsJson),
      })
      .then((run) => {
        if (!mountedRef.current) return;
        toast.success("回测已启动");
        pollRunIdRef.current = run.run_id;
        pollCountRef.current = 0;
        pollTimerRef.current = setTimeout(poll, 2000);
      })
      .catch(() => {
        if (mountedRef.current) {
          setBtLoading(false);
          toast.error("发起回测失败");
        }
      });
  };

  // 用于跨闭包访问的 ref
  const pollRunIdRef = useRef<number | null>(null);
  const pollCountRef = useRef(0);

  if (!isNew && isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Link href="/strategies">
          <ArrowLeft className="h-5 w-5 text-muted-foreground hover:text-foreground" />
        </Link>
        <h1 className="text-2xl font-bold">{isNew ? "新建策略" : "编辑策略"}</h1>
        {!isNew && strategy && (
          <Badge variant="secondary">
            {STRATEGY_STATUS_LABELS[strategy.status] ?? strategy.status}
          </Badge>
        )}
      </div>

      <Tabs defaultValue="edit">
        <TabsList>
          <TabsTrigger value="edit">策略编辑</TabsTrigger>
          {!isNew && <TabsTrigger value="backtest">回测</TabsTrigger>}
        </TabsList>

        {/* 编辑 */}
        <TabsContent value="edit">
          <Card>
            <CardContent className="space-y-4 p-6">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="space-y-1.5">
                  <Label htmlFor="name">策略名称 *</Label>
                  <Input
                    id="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="如：双均线策略"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="desc">描述</Label>
                  <Input
                    id="desc"
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="可选"
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="code">策略代码（backtrader） *</Label>
                <Textarea
                  id="code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  className="min-h-[240px] font-mono text-xs"
                  placeholder="import backtrader as bt&#10;..."
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="params">参数（JSON）</Label>
                <Textarea
                  id="params"
                  value={paramsJson}
                  onChange={(e) => setParamsJson(e.target.value)}
                  className="min-h-[80px] font-mono text-xs"
                />
              </div>

              <div className="flex justify-end">
                <Button
                  onClick={() => saveMutation.mutate()}
                  disabled={saveMutation.isPending || !name || !code}
                >
                  {saveMutation.isPending && (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  )}
                  {isNew ? "创建" : "保存"}
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 回测 */}
        {!isNew && (
          <TabsContent value="backtest">
            <div className="space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base">发起回测</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="bt-start">开始日期 *</Label>
                      <Input
                        id="bt-start"
                        type="date"
                        value={btStart}
                        onChange={(e) => setBtStart(e.target.value)}
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bt-end">结束日期 *</Label>
                      <Input
                        id="bt-end"
                        type="date"
                        value={btEnd}
                        onChange={(e) => setBtEnd(e.target.value)}
                      />
                    </div>
                  </div>
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-1.5">
                      <Label htmlFor="bt-capital">初始资金 *</Label>
                      <Input
                        id="bt-capital"
                        value={btCapital}
                        onChange={(e) => setBtCapital(e.target.value)}
                        placeholder="1000000"
                      />
                    </div>
                    <div className="space-y-1.5">
                      <Label htmlFor="bt-symbols">标的（逗号分隔）*</Label>
                      <Input
                        id="bt-symbols"
                        value={btSymbols}
                        onChange={(e) => setBtSymbols(e.target.value)}
                        placeholder="600519.SH,000001.SZ"
                      />
                    </div>
                  </div>
                  <div className="flex justify-end">
                    <Button
                      onClick={startBacktest}
                      disabled={
                        btLoading ||
                        !btStart ||
                        !btEnd ||
                        !btSymbols
                      }
                    >
                      {btLoading ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Play className="h-4 w-4" />
                      )}
                      {btLoading ? "回测中..." : "开始回测"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              {/* 回测结果 */}
              {btResult && (
                <Card>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base">回测结果</CardTitle>
                      <Badge
                        variant={
                          btResult.status === "success"
                            ? "success"
                            : btResult.status === "failed"
                            ? "danger"
                            : "warning"
                        }
                      >
                        {BACKTEST_STATUS_LABELS[btResult.status] ?? btResult.status}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {btResult.result ? (
                      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                        <MetricCard
                          label="总收益率"
                          value={formatPercent(btResult.result.total_return)}
                          raw={btResult.result.total_return}
                        />
                        <MetricCard
                          label="年化收益"
                          value={formatPercent(btResult.result.annual_return)}
                          raw={btResult.result.annual_return}
                        />
                        <MetricCard
                          label="最大回撤"
                          value={formatPercent(btResult.result.max_drawdown)}
                          danger
                        />
                        <MetricCard
                          label="夏普比率"
                          value={
                            btResult.result.sharpe_ratio?.toFixed(4) ?? "--"
                          }
                        />
                        <MetricCard
                          label="胜率"
                          value={formatPercent(btResult.result.win_rate)}
                        />
                        <MetricCard
                          label="交易次数"
                          value={
                            btResult.result.trade_count?.toString() ?? "--"
                          }
                        />
                      </div>
                    ) : btResult.error_message ? (
                      <p className="text-sm text-danger">
                        {btResult.error_message}
                      </p>
                    ) : (
                      <div className="flex items-center gap-2 text-sm text-muted-foreground">
                        <Loader2 className="h-4 w-4 animate-spin" />
                        等待回测完成...（如长时间未响应，请确认后端 strategy_worker 已启动）
                      </div>
                    )}
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>
        )}
      </Tabs>
    </div>
  );
}

function MetricCard({
  label,
  value,
  danger,
  raw,
}: {
  label: string;
  value: string;
  danger?: boolean;
  raw?: number | null;
}) {
  const colorClass = danger
    ? "text-danger"
    : raw !== null && raw !== undefined && raw > 0
    ? "text-up"
    : raw !== null && raw !== undefined && raw < 0
    ? "text-down"
    : "";
  return (
    <div className="rounded-lg border border-border p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`mt-1 text-xl font-bold tabular-nums ${colorClass}`}>
        {value}
      </p>
    </div>
  );
}
