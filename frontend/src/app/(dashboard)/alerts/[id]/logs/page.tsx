"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowLeft, Bell } from "lucide-react";
import { alertService } from "@/services/alerts";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState } from "@/components/layout/empty-state";
import { TableSkeleton } from "@/components/layout/loading-skeleton";
import { formatPrice, formatDateTimeSec } from "@/lib/format";

export default function AlertLogsPage() {
  const params = useParams<{ id: string }>();
  const ruleId = parseInt(params.id);

  const { data: logs, isLoading } = useQuery({
    queryKey: ["alert-logs", ruleId],
    queryFn: () => alertService.getLogs(ruleId),
  });

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-4">
        <Link href="/alerts">
          <ArrowLeft className="h-5 w-5 text-muted-foreground hover:text-foreground" />
        </Link>
        <h1 className="text-2xl font-bold">告警日志</h1>
      </div>

      <Card>
        <CardContent className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={5} cols={3} />
            </div>
          ) : !logs || logs.length === 0 ? (
            <EmptyState
              icon={Bell}
              title="暂无触发记录"
              description="该规则尚未触发过告警"
            />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>触发时间</TableHead>
                  <TableHead className="text-right">触发价格</TableHead>
                  <TableHead>详情</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {logs.map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="tabular-nums text-muted-foreground">
                      {formatDateTimeSec(log.triggered_at)}
                    </TableCell>
                    <TableCell className="text-right tabular-nums font-medium text-up">
                      {formatPrice(log.trigger_value)}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {log.message ?? "—"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
