import dayjs from "dayjs";
import { Clock3, ExternalLink, Sparkles } from "lucide-react";
import { StockAnalysisSection } from "@/components/panels/stock-analysis-section";
import type { StockAnalysis } from "@/types";

interface StockAnalysisContentProps {
  analysis: StockAnalysis;
}

export function StockAnalysisContent({ analysis }: StockAnalysisContentProps) {
  return (
    <div className="pb-3">
      <div className="border-b bg-primary/5 px-3 py-3">
        <div className="flex items-start gap-2">
          <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <p className="text-xs font-medium leading-5">{analysis.meta.trigger}</p>
        </div>
        <p className="mt-2 flex items-center gap-1 text-[10px] text-muted-foreground">
          <Clock3 className="h-3 w-3" />
          {dayjs(analysis.meta.generated_at).format("MM-DD HH:mm")}
        </p>
      </div>

      {analysis.sections.map((section, index) => (
        <StockAnalysisSection key={section.id} section={section} open={index === 0} />
      ))}

      {analysis.sources.length > 0 && (
        <div className="space-y-2 border-b px-3 py-3">
          <h4 className="text-[11px] font-semibold">公开来源 · {analysis.sources.length}</h4>
          {analysis.sources.map((source) => (
            <a
              key={`${source.url}-${source.title}`}
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="grid grid-cols-[18px_minmax(0,1fr)_14px] items-start gap-1 text-[11px] leading-4 text-primary hover:underline"
            >
              <span className="text-[10px] font-semibold text-muted-foreground">{analysis.sources.indexOf(source) + 1}</span>
              <span className="line-clamp-2">{source.source_name} · {source.title}</span>
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
