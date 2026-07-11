import api from "@/lib/api";
import type { AlertRule, AlertLog, AlertCondition } from "@/types";

export const alertService = {
  list: (params?: { rule_status?: string; symbol?: string }) =>
    api.get<AlertRule[]>("/alerts", { params }).then((r) => r.data),

  create: (data: {
    symbol: string;
    condition: AlertCondition;
    notify_channels?: string[];
    dedup_cooldown_minutes?: number;
    dedup_rearm_pct?: string;
  }) => api.post<AlertRule>("/alerts", data).then((r) => r.data),

  update: (
    ruleId: number,
    data: {
      condition?: AlertCondition;
      status?: "active" | "paused";
      dedup_cooldown_minutes?: number;
      dedup_rearm_pct?: string;
    }
  ) => api.patch<AlertRule>(`/alerts/${ruleId}`, data).then((r) => r.data),

  getLogs: (ruleId: number) =>
    api.get<AlertLog[]>(`/alerts/${ruleId}/logs`).then((r) => r.data),
};
