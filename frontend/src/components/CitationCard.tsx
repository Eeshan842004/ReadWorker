"use client";

import type { Source } from "@/lib/types";

export function CitationCard({ source, index }: { source: Source; index: number }) {
  const score = source.rrf_score ?? source.score;

  return (
    <div className="ak-transition group rounded-lg border border-border bg-card p-2.5 hover:border-brand/35 hover:shadow-sm">
      <div className="mb-1.5 flex items-center justify-between gap-2">
        <span className="rounded-full bg-brand-soft px-2 py-0.5 font-mono text-[10px] font-medium text-foreground">
          Source {index + 1}
        </span>
        <span className="font-mono text-[10px] text-muted-foreground">
          doc {source.document_id.slice(0, 8)}
          {typeof score === "number" ? ` · ${score.toFixed(3)}` : ""}
        </span>
      </div>
      <p className="line-clamp-4 text-[11px] leading-relaxed text-foreground/75">{source.content}</p>
    </div>
  );
}
