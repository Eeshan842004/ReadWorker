"use client";

import type { AgentNode, TraceEntry } from "@/lib/types";

export interface PipelineStep {
  key: AgentNode;
  label: string;
  doing: string;
}

export const PIPELINE_STEPS: PipelineStep[] = [
  { key: "query_clarifier", label: "Clarifier", doing: "Cleaning up your question" },
  { key: "planner", label: "Planner", doing: "Breaking it into sub-questions" },
  { key: "retriever", label: "Retriever", doing: "Searching your documents" },
  { key: "synthesizer", label: "Synthesizer", doing: "Writing a cited answer" },
  { key: "critic", label: "Critic", doing: "Fact-checking the answer" },
];

type StepState = "pending" | "active" | "done" | "warn" | "error";

function stepState(
  step: PipelineStep,
  lastByNode: Map<string, TraceEntry>,
  active: AgentNode | null,
): StepState {
  if (active === step.key) return "active";
  const last = lastByNode.get(step.key);
  if (!last) return "pending";
  if (last.status === "error" || last.status === "blocked") return "error";
  if (last.status === "warn") return "warn";
  return "done";
}

const DOT: Record<StepState, string> = {
  pending: "bg-muted-foreground/25",
  active: "bg-brand",
  done: "bg-success",
  warn: "bg-warning",
  error: "bg-destructive",
};

const CHIP: Record<StepState, string> = {
  pending: "border-border/70 bg-card/50 text-muted-foreground",
  active: "border-brand/45 bg-brand-soft text-foreground shadow-sm",
  done: "border-success/30 bg-card text-foreground",
  warn: "border-warning/40 bg-card text-foreground",
  error: "border-destructive/40 bg-card text-foreground",
};

export function LiveAgentTrace({
  trace,
  activeNode,
  running,
  faithfulness,
  latencyMs,
  retryCount = 0,
}: {
  trace: TraceEntry[];
  activeNode: AgentNode | null;
  running: boolean;
  faithfulness?: number | null;
  latencyMs?: number;
  retryCount?: number;
}) {
  // One pass over the trace: later entries overwrite earlier, so the map holds the
  // most recent entry per node — used for both "reached" checks and status coloring.
  const lastByNode = new Map<string, TraceEntry>();
  for (const entry of trace) lastByNode.set(entry.node, entry);
  const activeStep = PIPELINE_STEPS.find((s) => s.key === activeNode);

  return (
    <div className="ak-rise rounded-xl border border-border/80 bg-card/70 p-3 backdrop-blur-sm sm:p-4">
      {/* Pipeline rail */}
      <div className="flex flex-wrap items-center gap-x-1.5 gap-y-2">
        {PIPELINE_STEPS.map((step, i) => {
          const state = stepState(step, lastByNode, activeNode);
          const reached = state !== "pending";
          return (
            <div key={step.key} className="flex items-center gap-1.5">
              <div
                className={`ak-transition flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${CHIP[state]}`}
              >
                <span className="relative flex h-1.5 w-1.5">
                  {state === "active" ? (
                    <span className="ak-halo absolute inline-flex h-full w-full rounded-full bg-brand" />
                  ) : null}
                  <span className={`relative inline-flex h-1.5 w-1.5 rounded-full ${DOT[state]}`} />
                </span>
                {step.label}
              </div>

              {i < PIPELINE_STEPS.length - 1 ? (
                <div className="relative h-px w-4 overflow-hidden rounded-full bg-border sm:w-6">
                  <div
                    className={`ak-transition absolute inset-0 origin-left rounded-full bg-success/70 ${
                      reached && lastByNode.has(PIPELINE_STEPS[i + 1].key) ? "scale-x-100" : "scale-x-0"
                    }`}
                  />
                  {state === "active" ? (
                    <span className="ak-flow absolute inset-y-0 w-1/3 rounded-full bg-brand" />
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })}

        {retryCount > 0 ? (
          <span className="ak-pop ml-1 rounded-full border border-warning/40 bg-card px-2 py-0.5 text-[10px] font-medium text-foreground">
            ↺ re-retrieved ×{retryCount}
          </span>
        ) : null}
      </div>

      {/* Status line */}
      <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border/60 pt-2.5 text-[11px]">
        {running ? (
          <span className="flex items-center gap-1.5 text-foreground">
            <span className="ak-blink text-brand">●</span>
            {activeStep ? activeStep.doing : "Starting the pipeline"}
            <span className="ak-blink text-muted-foreground">…</span>
          </span>
        ) : (
          <span className="text-muted-foreground">Pipeline complete</span>
        )}

        <span className="ml-auto flex items-center gap-1.5">
          {typeof faithfulness === "number" ? (
            <span
              className={`rounded-full px-2 py-0.5 font-medium ${
                faithfulness >= 0.8
                  ? "bg-success/12 text-success"
                  : faithfulness >= 0.6
                    ? "bg-warning/15 text-warning"
                    : "bg-destructive/12 text-destructive"
              }`}
            >
              faithfulness {faithfulness.toFixed(2)}
            </span>
          ) : null}
          {typeof latencyMs === "number" && latencyMs > 0 ? (
            <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-muted-foreground">
              {(latencyMs / 1000).toFixed(1)}s
            </span>
          ) : null}
        </span>
      </div>

      {/* Trace log */}
      {trace.length > 0 ? (
        <details className="group mt-2.5">
          <summary className="ak-transition cursor-pointer list-none text-[11px] text-muted-foreground hover:text-foreground">
            <span className="inline-block transition-transform group-open:rotate-90">▸</span> View
            full trace ({trace.length} steps)
          </summary>
          <div className="mt-2 space-y-1.5">
            {trace.map((entry, i) => (
              <div
                key={i}
                className={`ak-rise border-l-2 pl-2.5 ${
                  entry.status === "error" || entry.status === "blocked"
                    ? "border-l-destructive"
                    : entry.status === "warn"
                      ? "border-l-warning"
                      : "border-l-success/60"
                }`}
              >
                <p className="font-mono text-[10px] font-medium text-foreground">{entry.node}</p>
                <p className="text-[11px] leading-relaxed text-muted-foreground">{entry.message}</p>
              </div>
            ))}
          </div>
        </details>
      ) : null}
    </div>
  );
}
