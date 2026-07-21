"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { Button } from "@/components/ui/button";
import {
  getCostSummary,
  getEvalQuestions,
  getEvalResults,
  getEvalStatus,
  runEval,
} from "@/lib/api";
import type { CostSummary, EvalQuestionsResponse, EvalResults } from "@/lib/types";

const METRIC_TARGETS: Record<string, number> = {
  faithfulness: 0.9,
  answer_relevancy: 0.85,
  context_precision: 0.85,
  context_recall: 0.8,
};

export function EvalDashboard() {
  const [results, setResults] = useState<EvalResults | null>(null);
  const [cost, setCost] = useState<CostSummary | null>(null);
  const [testSets, setTestSets] = useState<EvalQuestionsResponse | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const [r, c, q] = await Promise.all([
      getEvalResults().catch(() => null),
      getCostSummary().catch(() => null),
      getEvalQuestions().catch(() => null),
    ]);
    if (r) setResults(r);
    if (c) setCost(c);
    if (q) setTestSets(q);
  }, []);

  const startPolling = useCallback(() => {
    setRunning(true);
    if (pollRef.current) clearInterval(pollRef.current);
    pollRef.current = setInterval(() => {
      void (async () => {
        const status = await getEvalStatus().catch(() => ({ in_progress: false }));
        if (!status.in_progress) {
          if (pollRef.current) clearInterval(pollRef.current);
          pollRef.current = null;
          setRunning(false);
          await refresh();
        }
      })();
    }, 3000);
  }, [refresh]);

  useEffect(() => {
    let active = true;
    (async () => {
      const status = await getEvalStatus().catch(() => ({ in_progress: false }));
      if (!active) return;
      if (status.in_progress) startPolling();
      await refresh();
    })();
    const poll = pollRef;
    return () => {
      active = false;
      if (poll.current) clearInterval(poll.current);
    };
  }, [refresh, startPolling]);

  const trigger = async (documentId?: string) => {
    setError(null);
    try {
      const res = await runEval(documentId);
      if (res.status === "started" || res.status === "already_running") startPolling();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start eval");
    }
  };

  const chartData = Object.entries(results?.summary ?? {}).map(([metric, value]) => ({
    metric: metric.replace(/_/g, " "),
    key: metric,
    value: Number(value),
    target: METRIC_TARGETS[metric] ?? 0.85,
  }));

  const totalQuestions = testSets?.total_questions ?? 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="max-w-lg text-xs leading-relaxed text-muted-foreground">
          Each document gets its own test set. Run <strong>one document&apos;s</strong> eval to
          grade it on <em>only its own</em> questions — or run all of them together.
        </p>
        <Button
          size="sm"
          variant="outline"
          onClick={() => void trigger()}
          disabled={running || totalQuestions === 0}
          className="ak-transition rounded-lg hover:-translate-y-0.5"
        >
          {running ? "Evaluating…" : totalQuestions === 0 ? "No test set yet" : `Run all (${totalQuestions} Q)`}
        </Button>
      </div>

      {/* Attached test sets */}
      <div className="rounded-2xl border border-brand/40 bg-brand-soft/30 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span>📎</span>
          <h2 className="text-sm font-semibold">Test questions attached to Eval</h2>
        </div>
        {totalQuestions === 0 ? (
          <p className="text-xs text-muted-foreground">
            No test set yet.{" "}
            <Link href="/" className="text-brand underline-offset-2 hover:underline">
              Upload a document
            </Link>{" "}
            — a test set is written automatically, then it shows up here to grade against.
          </p>
        ) : (
          <div className="space-y-2">
            <p className="text-xs text-muted-foreground">
              {totalQuestions} auto-generated question{totalQuestions === 1 ? "" : "s"} across{" "}
              {testSets?.sets.length} document{testSets?.sets.length === 1 ? "" : "s"}. These are what
              the RAG agent is graded on.
            </p>
            {testSets?.sets.map((s) => (
              <details key={s.document_id} className="group rounded-lg border border-border bg-card p-2.5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-2">
                  <span className="flex min-w-0 items-center gap-2 text-[13px] font-medium">
                    <span>📄</span>
                    <span className="line-clamp-1">{s.filename}</span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className="rounded-full bg-brand-soft px-2 py-0.5 font-mono text-[10px] font-medium">
                      {s.count} Q
                    </span>
                    <Button
                      size="sm"
                      onClick={(e) => {
                        e.preventDefault();
                        void trigger(s.document_id);
                      }}
                      disabled={running}
                      className="ak-transition h-7 rounded-lg px-2.5 text-[11px]"
                    >
                      {running ? "…" : "Run eval →"}
                    </Button>
                  </span>
                </summary>
                <ul className="mt-2 space-y-1 border-t border-border pt-2">
                  {s.samples.map((q, i) => (
                    <li key={i} className="text-[11px] leading-relaxed text-muted-foreground">
                      • {q}
                    </li>
                  ))}
                  {s.count > s.samples.length ? (
                    <li className="text-[11px] text-muted-foreground/70">
                      …and {s.count - s.samples.length} more
                    </li>
                  ) : null}
                </ul>
              </details>
            ))}
          </div>
        )}
      </div>

      {running ? (
        <p className="ak-pop flex items-center gap-2 rounded-lg border border-brand/40 bg-card px-3 py-2 text-xs text-foreground">
          <span className="ak-blink text-brand">●</span> Grading the RAG agent against{" "}
          {totalQuestions} question{totalQuestions === 1 ? "" : "s"}… this takes ~1–2 min. Results
          appear below automatically.
        </p>
      ) : null}

      <details className="ak-transition group rounded-xl border border-border bg-card/60 px-4 py-3">
        <summary className="cursor-pointer list-none text-sm font-medium">
          <span className="inline-block transition-transform group-open:rotate-90">▸</span> How this
          page works &amp; how to use it
        </summary>
        <div className="mt-3 space-y-3 text-[13px] leading-relaxed text-muted-foreground">
          <p>
            This page answers one question: <strong className="text-foreground">is the RAG
            actually giving good answers, or does it just look busy?</strong> It has two parts.
          </p>
          <div>
            <p className="font-medium text-foreground">1. Live usage stats (top row) — automatic</p>
            <p>
              Every question you ask anywhere in the app is logged. The <em>Queries</em>,{" "}
              <em>Tokens</em>, <em>Total cost</em>, and <em>Avg latency</em> tiles update on their
              own — nothing to set up. Cost stays $0 on the free tier.
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground">2. Quality metrics (chart) — you trigger it</p>
            <p>
              The bar chart scores retrieval and answer quality with{" "}
              <span className="font-mono text-[11px]">ragas</span> — faithfulness, answer relevancy,
              context precision/recall. It needs a <em>golden set</em>: questions paired with their
              correct answers, so the grader has a reference to compare against.
            </p>
          </div>
          <div>
            <p className="font-medium text-foreground">The test set builds itself (2 steps)</p>
            <ol className="list-decimal space-y-1 pl-5">
              <li>
                <strong className="text-foreground">Upload a document.</strong> As it&apos;s
                ingested, an LLM automatically writes ~5 questions with known answers from it — you
                watch them appear live. They attach to this page (see the panel above).
              </li>
              <li>
                Click <strong className="text-foreground">Run evaluation</strong>. The RAG agent
                answers each question, ragas grades it, and the chart fills in — green = meets
                target, amber = below. Takes ~1–2 min.
              </li>
            </ol>
          </div>
          <p className="text-[12px]">
            Interview tip: because the test set is generated from the very document under test, this
            is a genuine self-grading loop — the numbers reflect this corpus, not a canned demo.
          </p>
        </div>
      </details>

      {error ? (
        <p className="ak-pop rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
        <Stat label="Queries" value={cost?.total_queries ?? "—"} />
        <Stat label="Tokens" value={cost?.total_tokens?.toLocaleString() ?? "—"} />
        <Stat label="Total cost" value={`$${(cost?.total_cost_usd ?? 0).toFixed(4)}`} accent />
        <Stat
          label="Avg latency"
          value={cost ? `${(cost.avg_latency_ms / 1000).toFixed(1)}s` : "—"}
        />
      </div>

      <div className="rounded-2xl border border-border bg-card p-4 shadow-sm">
        <div className="mb-3 flex items-center justify-between gap-2">
          <div>
            <h2 className="text-sm font-medium">ragas metrics vs target</h2>
            {chartData.length > 0 ? (
              <p className="text-[11px] text-muted-foreground">
                {results?.document_name
                  ? `Scored: ${results.document_name} (${results?.num_questions ?? ""} questions)`
                  : `Scored: all documents (${results?.num_questions ?? ""} questions)`}
              </p>
            ) : null}
          </div>
          {results?.gate ? (
            <span
              className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
                results.gate.passed
                  ? "bg-success/12 text-success"
                  : "bg-destructive/12 text-destructive"
              }`}
            >
              CI gate: {results.gate.passed ? "PASS" : "FAIL"}
            </span>
          ) : null}
        </div>

        {chartData.length === 0 ? (
          <div className="rounded-xl border border-dashed border-border bg-muted/20 p-8 text-center">
            <p className="text-sm font-medium">No evaluation results yet</p>
            <p className="mx-auto mt-1 max-w-md text-xs leading-relaxed text-muted-foreground">
              {totalQuestions === 0
                ? "Upload a document first — its test set is generated automatically, then Run evaluation."
                : "Click Run evaluation above to grade the RAG agent against the attached test set. Metrics appear here."}
            </p>
          </div>
        ) : (
          <div className="h-72 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                <XAxis
                  dataKey="metric"
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis
                  domain={[0, 1]}
                  tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  axisLine={false}
                  tickLine={false}
                />
                <Tooltip
                  cursor={{ fill: "var(--muted)", opacity: 0.4 }}
                  contentStyle={{
                    borderRadius: 10,
                    border: "1px solid var(--border)",
                    background: "var(--card)",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="value" radius={[6, 6, 0, 0]} maxBarSize={64}>
                  {chartData.map((d) => (
                    <Cell
                      key={d.key}
                      fill={d.value >= d.target ? "var(--success)" : "var(--warning)"}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: string | number;
  accent?: boolean;
}) {
  return (
    <div className="ak-transition rounded-xl border border-border bg-card p-3 shadow-sm hover:shadow-md">
      <p className="text-[11px] text-muted-foreground">{label}</p>
      <p className={`mt-0.5 text-lg font-semibold ${accent ? "text-success" : ""}`}>{value}</p>
    </div>
  );
}
