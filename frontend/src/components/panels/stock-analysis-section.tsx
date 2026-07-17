import {
  ChartNoAxesCombined,
  ChevronDown,
  CircleAlert,
  FileSearch,
  Network,
  ShieldAlert,
} from "lucide-react";
import type { AnalysisSection } from "@/types";

const SECTION_META = {
  event_core: { icon: FileSearch, tone: "text-primary bg-primary/10" },
  topic_mapping: { icon: Network, tone: "text-warning bg-warning/10" },
  candidate_stocks: { icon: ChartNoAxesCombined, tone: "text-success bg-success/10" },
  risk_checklist: { icon: ShieldAlert, tone: "text-danger bg-danger/10" },
} as const;

const FIELD_LABELS: Record<string, string> = {
  summary: "事实摘要",
  impact: "潜在影响",
  transmission_path: "传导路径",
  topic: "主题",
  relationship: "关联",
  evidence: "依据",
  symbol: "代码",
  name: "名称",
  logic: "影响逻辑",
  uncertainty: "不确定性",
  risk: "风险",
  verification: "核验方式",
};

export function StockAnalysisSection({ section, open }: { section: AnalysisSection; open: boolean }) {
  const meta = SECTION_META[section.id];
  const Icon = meta.icon;

  return (
    <details className="group border-b px-3 py-2" open={open}>
      <summary className="flex cursor-pointer list-none items-center gap-2 py-1">
        <span className={`flex h-6 w-6 items-center justify-center rounded ${meta.tone}`}>
          <Icon className="h-3.5 w-3.5" />
        </span>
        <span className="min-w-0 flex-1 truncate text-xs font-semibold">{section.title}</span>
        <ChevronDown className="h-3.5 w-3.5 text-muted-foreground transition-transform group-open:rotate-180" />
      </summary>
      <div className="pt-2">
        <SectionBody section={section} />
      </div>
    </details>
  );
}

function SectionBody({ section }: { section: AnalysisSection }) {
  if (!Array.isArray(section.content)) return <ObjectRows content={section.content} />;
  if (section.content.length === 0) return <p className="text-xs text-muted-foreground">暂无可靠结果</p>;
  if (section.id === "candidate_stocks") return <CandidateRows rows={section.content} />;
  if (section.id === "topic_mapping") return <TopicRows rows={section.content} />;

  return (
    <div className="space-y-2">
      {section.content.map((row, index) => (
        <div key={index} className="grid grid-cols-[18px_minmax(0,1fr)] gap-2 border-b border-border/50 pb-2 last:border-0">
          <CircleAlert className="mt-0.5 h-3.5 w-3.5 text-danger" />
          <ObjectRows content={row} compact />
        </div>
      ))}
    </div>
  );
}

function CandidateRows({ rows }: { rows: Array<Record<string, unknown>> }) {
  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <div key={index} className="border-b border-border/60 pb-2 last:border-0">
          <div className="flex items-center gap-2">
            <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">{value(row.symbol)}</span>
            <span className="text-xs font-semibold">{value(row.name)}</span>
          </div>
          <p className="mt-1.5 text-[11px] leading-4">{value(row.logic)}</p>
          {row.uncertainty != null && (
            <p className="mt-1 flex gap-1 text-[10px] leading-4 text-warning">
              <CircleAlert className="mt-0.5 h-3 w-3 shrink-0" />{value(row.uncertainty)}
            </p>
          )}
        </div>
      ))}
    </div>
  );
}

function TopicRows({ rows }: { rows: Array<Record<string, unknown>> }) {
  return (
    <div className="space-y-2">
      {rows.map((row, index) => (
        <div key={index} className="border-l-2 border-warning/60 pl-2">
          <span className="inline-flex rounded bg-warning/10 px-1.5 py-0.5 text-[10px] font-medium text-warning">{value(row.topic)}</span>
          <p className="mt-1 text-[11px] leading-4">{value(row.relationship)}</p>
          {row.evidence != null && <p className="mt-1 text-[10px] leading-4 text-muted-foreground">{value(row.evidence)}</p>}
        </div>
      ))}
    </div>
  );
}

function ObjectRows({ content, compact = false }: { content: Record<string, unknown>; compact?: boolean }) {
  return (
    <dl className={compact ? "space-y-1" : "space-y-2.5"}>
      {Object.entries(content).map(([key, item]) => (
        <div key={key}>
          <dt className="text-[10px] font-medium text-muted-foreground">{FIELD_LABELS[key] ?? key}</dt>
          <dd className="mt-0.5 text-[11px] leading-4">{value(item)}</dd>
        </div>
      ))}
    </dl>
  );
}

function value(item: unknown) {
  if (item === null || item === undefined || item === "") return "--";
  return typeof item === "string" ? item : JSON.stringify(item);
}
