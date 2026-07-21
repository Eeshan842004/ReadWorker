"use client";

import { useEffect, useRef, useState } from "react";

import { LiveAgentTrace, PIPELINE_STEPS } from "@/components/LiveAgentTrace";
import { Button } from "@/components/ui/button";
import type { AgentNode, TraceEntry } from "@/lib/types";

const SCRIPT: { node: AgentNode; entry: TraceEntry; delay: number }[] = [
  {
    node: "query_clarifier",
    delay: 900,
    entry: {
      node: "query_clarifier",
      status: "ok",
      message: "'wat is rag' → 'What is retrieval-augmented generation?'",
    },
  },
  {
    node: "planner",
    delay: 1100,
    entry: { node: "planner", status: "ok", message: "decomposed into 2 sub-question(s)" },
  },
  {
    node: "retriever",
    delay: 1300,
    entry: { node: "retriever", status: "ok", message: "found 9 unique chunks, reranked to 7" },
  },
  {
    node: "synthesizer",
    delay: 1400,
    entry: { node: "synthesizer", status: "ok", message: "generated 812 chars, 7 citations" },
  },
  {
    node: "critic",
    delay: 1000,
    entry: {
      node: "critic",
      status: "ok",
      message: "faithfulness=0.91, issues='none', retry=False",
    },
  },
];

export function PipelineExplainer() {
  const [step, setStep] = useState(SCRIPT.length);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearTimers = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };

  useEffect(() => clearTimers, []);

  const play = () => {
    clearTimers();
    setStep(0);
    let elapsed = 0;
    SCRIPT.forEach((s, i) => {
      elapsed += s.delay;
      timers.current.push(setTimeout(() => setStep(i + 1), elapsed));
    });
  };

  const running = step < SCRIPT.length;
  const trace = SCRIPT.slice(0, step).map((s) => s.entry);
  const activeNode = running ? SCRIPT[step].node : null;

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          onClick={play}
          disabled={running}
          className="ak-transition rounded-lg hover:-translate-y-0.5"
        >
          {running ? "Running…" : "▶ Replay a run"}
        </Button>
        <p className="text-[11px] text-muted-foreground">
          This is the same component the chat uses — driven by real SSE events there.
        </p>
      </div>

      <LiveAgentTrace
        trace={trace}
        activeNode={activeNode}
        running={running}
        faithfulness={running ? null : 0.91}
        latencyMs={running ? 0 : 5700}
      />

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {PIPELINE_STEPS.map((s, i) => (
          <div key={s.key} className="rounded-xl border border-border bg-card p-3 shadow-sm">
            <div className="mb-1 flex items-center gap-2">
              <span className="flex h-5 w-5 items-center justify-center rounded-md bg-brand-soft font-mono text-[10px] font-semibold">
                {i + 1}
              </span>
              <p className="text-xs font-medium">{s.label}</p>
            </div>
            <p className="text-[11px] leading-relaxed text-muted-foreground">{s.doing}</p>
          </div>
        ))}
        <div className="rounded-xl border border-dashed border-warning/40 bg-card p-3 shadow-sm">
          <div className="mb-1 flex items-center gap-2">
            <span className="flex h-5 w-5 items-center justify-center rounded-md bg-warning/15 text-[10px]">
              ↺
            </span>
            <p className="text-xs font-medium">Re-retrieval loop</p>
          </div>
          <p className="text-[11px] leading-relaxed text-muted-foreground">
            If the Critic scores faithfulness below 0.7, it sends the question back to the Retriever
            with a wider net — up to 2 times.
          </p>
        </div>
      </div>
    </div>
  );
}
