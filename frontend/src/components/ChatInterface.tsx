"use client";

import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";

import { CitationCard } from "@/components/CitationCard";
import { DocumentSelect } from "@/components/DocumentSelect";
import { LiveAgentTrace } from "@/components/LiveAgentTrace";
import { ModeToggle, type ChatMode } from "@/components/ModeToggle";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { askAgenticStream, askQuestion } from "@/lib/api";
import type { AgentNode, ChatMessage, DocumentSummary, StreamEvent, TraceEntry } from "@/lib/types";

const SUGGESTIONS = [
  "Give me a concise summary of this document.",
  "What are the key points covered?",
  "What questions does this document answer?",
];

interface ChatInterfaceProps {
  messages: ChatMessage[];
  setMessages: (updater: (prev: ChatMessage[]) => ChatMessage[]) => void;
  documents: DocumentSummary[];
  activeDocId: string | null;
  onSelectDoc: (docId: string | null) => void;
}

export function ChatInterface({
  messages,
  setMessages,
  documents,
  activeDocId,
  onSelectDoc,
}: ChatInterfaceProps) {
  const [input, setInput] = useState("");
  const [mode, setMode] = useState<ChatMode>("agentic");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Live pipeline state for the in-flight question.
  const [liveTrace, setLiveTrace] = useState<TraceEntry[]>([]);
  const [activeNode, setActiveNode] = useState<AgentNode | null>(null);
  const [liveRetries, setLiveRetries] = useState(0);

  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    requestAnimationFrame(() =>
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" }),
    );
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, liveTrace, scrollToBottom]);

  const send = async (question: string) => {
    if (!question.trim() || loading) return;
    setInput("");
    setError(null);
    setLiveTrace([]);
    setActiveNode(null);
    setLiveRetries(0);
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    setLoading(true);

    const scope = activeDocId ? [activeDocId] : [];

    try {
      if (mode === "single") {
        const res = await askQuestion(question, 5, scope);
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: res.answer, sources: res.sources },
        ]);
      } else {
        // The pipeline order is fixed, so the node that just finished tells us what runs next.
        const NEXT: Record<string, AgentNode | null> = {
          query_clarifier: "planner",
          planner: "retriever",
          retriever: "synthesizer",
          synthesizer: "critic",
          critic: null,
        };
        setActiveNode("query_clarifier");

        await askAgenticStream(
          question,
          (event: StreamEvent) => {
          if (event.type === "node_complete") {
            setLiveTrace((prev) => [...prev, ...event.trace]);
            setActiveNode(NEXT[event.node] ?? null);
            if (event.node === "retriever") {
              setLiveRetries((r) => (liveTraceHasRetried(event.trace) ? r + 1 : r));
            }
          } else if (event.type === "error") {
            setError(event.message);
          } else if (event.type === "done") {
            setActiveNode(null);
            setMessages((prev) => [
              ...prev,
              {
                role: "assistant",
                content: event.blocked
                  ? `🛡️ Blocked by guardrails: ${event.block_reason}`
                  : event.answer || "No answer was produced (the model may be rate-limited).",
                sources: event.sources,
                trace: event.trace_log,
                faithfulness: event.faithfulness_score,
                latencyMs: event.latency_ms,
                retryCount: event.retry_count,
              },
            ]);
          }
          },
          [],
          scope,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
    } finally {
      setLoading(false);
      setActiveNode(null);
      setLiveTrace([]);
    }
  };

  return (
    <div className="flex h-full flex-col gap-3">
      <ModeToggle mode={mode} onChange={setMode} disabled={loading} />

      {/* Which document this chat is grounded in */}
      {documents.length > 0 ? (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-card/60 px-3 py-2">
          <span className="text-[11px] font-medium text-muted-foreground">📎 Grounded in</span>
          <DocumentSelect
            documents={documents}
            value={activeDocId}
            onChange={onSelectDoc}
            disabled={loading || messages.length > 0}
          />
          {messages.length > 0 ? (
            <span className="text-[10px] text-muted-foreground">(new chat to switch)</span>
          ) : null}
        </div>
      ) : (
        <div className="rounded-xl border border-dashed border-border bg-card/40 px-3 py-2 text-[11px] text-muted-foreground">
          No documents uploaded yet —{" "}
          <Link href="/" className="text-brand underline-offset-2 hover:underline">
            upload one
          </Link>{" "}
          to ground your answers.
        </div>
      )}

      <div ref={scrollRef} className="flex-1 space-y-5 overflow-y-auto pr-1">
        {messages.length === 0 && !loading ? (
          <div className="ak-rise flex flex-col items-center justify-center gap-4 pt-8 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl border border-border bg-card text-xl shadow-sm">
              🧠
            </div>
            <div className="space-y-1">
              <p className="text-sm font-medium">Ask anything about your documents</p>
              <p className="text-xs text-muted-foreground">
                Every answer is grounded in your uploads and cited.
              </p>
            </div>
            <div className="flex flex-wrap justify-center gap-2 pt-1">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => void send(s)}
                  className="ak-transition rounded-full border border-border bg-card px-3 py-1.5 text-xs text-muted-foreground hover:-translate-y-0.5 hover:border-brand/50 hover:text-foreground hover:shadow-sm"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((msg, i) =>
          msg.role === "user" ? (
            <div key={i} className="ak-rise flex justify-end">
              <div className="max-w-[78%] rounded-2xl rounded-br-md bg-primary px-4 py-2.5 text-sm leading-relaxed text-primary-foreground shadow-sm">
                {msg.content}
              </div>
            </div>
          ) : (
            <div key={i} className="ak-rise space-y-2.5">
              {msg.trace && msg.trace.length > 0 ? (
                <LiveAgentTrace
                  trace={msg.trace}
                  activeNode={null}
                  running={false}
                  faithfulness={msg.faithfulness}
                  latencyMs={msg.latencyMs}
                  retryCount={msg.retryCount ?? 0}
                />
              ) : null}

              <div className="rounded-2xl rounded-tl-md border border-border bg-card px-4 py-3 text-sm leading-[1.7] whitespace-pre-wrap shadow-sm">
                {msg.content}
              </div>

              {msg.sources && msg.sources.length > 0 ? (
                <details className="group">
                  <summary className="ak-transition cursor-pointer list-none text-xs text-muted-foreground hover:text-foreground">
                    <span className="inline-block transition-transform group-open:rotate-90">▸</span>{" "}
                    {msg.sources.length} sources
                  </summary>
                  <div className="mt-2 grid grid-cols-1 gap-2 sm:grid-cols-2">
                    {msg.sources.map((source, si) => (
                      <CitationCard key={source.id} source={source} index={si} />
                    ))}
                  </div>
                </details>
              ) : null}
            </div>
          ),
        )}

        {/* In-flight pipeline */}
        {loading && mode === "agentic" ? (
          <LiveAgentTrace trace={liveTrace} activeNode={activeNode} running retryCount={liveRetries} />
        ) : null}

        {loading && mode === "single" ? (
          <div className="ak-rise flex items-center gap-2 rounded-2xl border border-border bg-card px-4 py-3 text-sm text-muted-foreground shadow-sm">
            <span className="ak-blink text-brand">●</span> Retrieving and answering…
          </div>
        ) : null}
      </div>

      {error ? (
        <p className="ak-pop rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      <div className="ak-transition flex items-end gap-2 rounded-2xl border border-border bg-card p-2 shadow-sm focus-within:border-brand/60 focus-within:shadow-md">
        <Textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void send(input);
            }
          }}
          disabled={loading}
          placeholder="Ask a question…  (Enter to send, Shift+Enter for a new line)"
          className="max-h-40 min-h-[44px] resize-none border-0 bg-transparent px-2 py-2.5 text-sm shadow-none focus-visible:ring-0 dark:bg-transparent"
        />
        <Button
          onClick={() => void send(input)}
          disabled={loading || !input.trim()}
          className="ak-transition h-9 shrink-0 rounded-xl px-4 hover:-translate-y-0.5"
        >
          {loading ? "…" : "Send"}
        </Button>
      </div>
    </div>
  );
}

function liveTraceHasRetried(trace: TraceEntry[]): boolean {
  return trace.some((t) => typeof t.message === "string" && t.message.includes("retry"));
}
