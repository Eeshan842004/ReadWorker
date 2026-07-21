"use client";

import type { GeneratedQa } from "@/lib/types";

interface QaGenerationViewProps {
  pairs: GeneratedQa[];
  expected: number | null;
  active: boolean;
  complete: boolean;
}

export function QaGenerationView({ pairs, expected, active, complete }: QaGenerationViewProps) {
  if (pairs.length === 0 && !active) return null;

  return (
    <div className="ak-rise space-y-3 rounded-xl border border-brand/40 bg-brand-soft/40 p-3 sm:p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          {complete ? (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success/20 text-[9px] text-success">
              ✓
            </span>
          ) : (
            <span className="ak-blink text-brand">✍️</span>
          )}
          <span className="font-medium">
            {complete ? "Test set ready — attached to Eval" : "Writing evaluation test set…"}
          </span>
        </div>
        <span className="rounded-full border border-brand/40 bg-card px-2 py-0.5 font-mono text-[11px] font-medium text-foreground">
          {pairs.length}
          {expected ? ` / ${expected}` : ""} questions
        </span>
      </div>

      <p className="text-[11px] leading-relaxed text-muted-foreground">
        An LLM is reading your document and writing questions with known answers — these become
        the golden set your RAG agent is graded against on the <strong>Eval</strong> page.
      </p>

      <div className="space-y-2">
        {pairs.map((qa) => (
          <div key={qa.index} className="ak-rise rounded-lg border border-border bg-card p-2.5">
            <div className="flex items-start gap-2">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-md bg-brand-soft font-mono text-[9px] font-semibold">
                {qa.index + 1}
              </span>
              <div className="min-w-0">
                <p className="text-[12.5px] font-medium leading-snug text-foreground">
                  {qa.question}
                </p>
                <p className="mt-1 line-clamp-2 text-[11px] leading-relaxed text-muted-foreground">
                  <span className="font-medium text-success">A:</span> {qa.answer}
                </p>
              </div>
            </div>
          </div>
        ))}

        {active && !complete ? (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-brand/40 bg-card/50 px-2.5 py-2 text-[11px] text-muted-foreground">
            <span className="ak-blink text-brand">●</span> thinking of the next question…
          </div>
        ) : null}
      </div>
    </div>
  );
}
