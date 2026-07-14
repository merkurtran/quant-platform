import { ExternalLink } from "lucide-react";
import type { AnalysisSection, StockAnalysis } from "@/types";

interface StockAnalysisContentProps {
  analysis: StockAnalysis;
}

const FIELD_LABELS: Record<string, string> = {
  summary: "事实摘要",
  impact: "潜在影响",
  transmission_path: "传导路径",
  topic: "主题",
  relationship: "关系",
  evidence: "证据",
  symbol: "代码",
  name: "名称",
  logic: "影响逻辑",
  uncertainty: "不确定性",
  risk: "风险",
  verification: "核验方式",
};

const TABLE_FIELDS: Partial<Record<AnalysisSection["id"], string[]>> = {
  topic_mapping: ["topic", "relationship", "evidence"],
  candidate_stocks: ["symbol", "name", "logic", "evidence", "uncertainty"],
};

function displayValue(value: unknown) {
  if (value === null || value === undefined || value === "") return "--";
  return typeof value === "string" ? value : JSON.stringify(value);
}

function ObjectContent({ content }: { content: Record<string, unknown> }) {
  return (
    <dl className="space-y-2">
      {Object.entries(content).map(([key, value]) => (
        <div key={key}>
          <dt className="text-[10px] text-muted-foreground">
            {FIELD_LABELS[key] ?? key}
          </dt>
          <dd className="mt-0.5 text-xs leading-5">{displayValue(value)}</dd>
        </div>
      ))}
    </dl>
  );
}

function ListContent({ section }: { section: AnalysisSection }) {
  const rows = Array.isArray(section.content) ? section.content : [];
  const fields = TABLE_FIELDS[section.id];

  if (rows.length === 0) {
    return <p className="text-xs text-muted-foreground">暂无可靠映射结果</p>;
  }

  if (fields) {
    return (
      <div className="overflow-x-auto">
        <table className="w-full min-w-[420px] border-collapse text-left text-[11px]">
          <thead className="text-muted-foreground">
            <tr>
              {fields.map((field) => (
                <th key={field} className="border-b py-1.5 pr-3 font-medium">
                  {FIELD_LABELS[field] ?? field}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index} className="align-top">
                {fields.map((field) => (
                  <td key={field} className="border-b border-border/60 py-2 pr-3 leading-4">
                    {displayValue(row[field])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {rows.map((row, index) => (
        <li key={index} className="border-l-2 border-border pl-2">
          <ObjectContent content={row} />
        </li>
      ))}
    </ul>
  );
}

export function StockAnalysisContent({ analysis }: StockAnalysisContentProps) {
  return (
    <div className="space-y-3 pb-3">
      <p className="border-b px-3 pb-3 text-xs leading-5 text-muted-foreground">
        {analysis.meta.trigger}
      </p>

      {analysis.sections.map((section, index) => (
        <details key={section.id} className="group border-b px-3 pb-3" open={index === 0}>
          <summary className="cursor-pointer list-none py-1 text-xs font-semibold">
            {section.title}
          </summary>
          <div className="pt-2">
            {Array.isArray(section.content) ? (
              <ListContent section={section} />
            ) : (
              <ObjectContent content={section.content} />
            )}
          </div>
        </details>
      ))}

      {analysis.sources.length > 0 && (
        <div className="space-y-1.5 px-3">
          <h4 className="text-[11px] font-semibold">公开来源</h4>
          {analysis.sources.map((source) => (
            <a
              key={`${source.url}-${source.title}`}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="flex items-start gap-1 text-[11px] leading-4 text-primary hover:underline"
            >
              <span className="line-clamp-2 flex-1">{source.source_name} · {source.title}</span>
              <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
            </a>
          ))}
        </div>
      )}

      <p className="px-3 text-[10px] leading-4 text-muted-foreground">
        {analysis.disclaimer}
      </p>
    </div>
  );
}
