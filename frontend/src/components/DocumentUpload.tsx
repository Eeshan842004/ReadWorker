"use client";

import Link from "next/link";
import { useCallback, useRef, useState } from "react";

import { ChunkVisualizer } from "@/components/ChunkVisualizer";
import { QaGenerationView } from "@/components/QaGenerationView";
import { Button, buttonVariants } from "@/components/ui/button";
import { ingestWsUrl, uploadDocument } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ChunkCreatedEvent, GeneratedQa, IngestWsEvent } from "@/lib/types";

type Status = "idle" | "uploading" | "complete" | "error";

export function DocumentUpload({ onUploaded }: { onUploaded?: () => void }) {
  const [status, setStatus] = useState<Status>("idle");
  const [chunks, setChunks] = useState<ChunkCreatedEvent[]>([]);
  const [totalExpected, setTotalExpected] = useState<number | null>(null);
  const [parentCount, setParentCount] = useState<number | null>(null);
  const [chunksComplete, setChunksComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  // Live evaluation test-set generation.
  const [qaPairs, setQaPairs] = useState<GeneratedQa[]>([]);
  const [qaExpected, setQaExpected] = useState<number | null>(null);
  const [qaActive, setQaActive] = useState(false);
  const [qaComplete, setQaComplete] = useState(false);
  const [uploadedDocId, setUploadedDocId] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    async (file: File) => {
      setStatus("uploading");
      setChunks([]);
      setTotalExpected(null);
      setParentCount(null);
      setChunksComplete(false);
      setQaPairs([]);
      setQaExpected(null);
      setQaActive(false);
      setQaComplete(false);
      setError(null);
      setFileName(file.name);

      const documentId = crypto.randomUUID();

      // Open the WebSocket first so no early chunk events are missed.
      const ws = new WebSocket(ingestWsUrl(documentId));
      const socketReady = new Promise<void>((resolve) => {
        ws.onopen = () => resolve();
        ws.onerror = () => resolve(); // upload still works without the live view
      });

      ws.onmessage = (event) => {
        const data: IngestWsEvent = JSON.parse(event.data);
        switch (data.type) {
          case "chunk_created":
            setChunks((prev) => [...prev, data]);
            break;
          case "chunking_summary":
            setTotalExpected(data.children);
            setParentCount(data.parents);
            break;
          case "ingest_complete":
            setTotalExpected(data.total_chunks);
            setChunksComplete(true);
            break;
          case "qa_generation_start":
            setQaActive(true);
            setQaExpected(data.expected);
            break;
          case "qa_generated":
            setQaPairs((prev) => [
              ...prev,
              { index: data.index, question: data.question, answer: data.answer },
            ]);
            break;
          case "qa_complete":
            setQaActive(false);
            setQaComplete(true);
            break;
          case "qa_generation_error":
            setQaActive(false);
            break;
        }
      };

      try {
        await socketReady;
        // Resolves after the whole flow (chunk + embed + store + test-set) completes.
        await uploadDocument(file, documentId);
        setUploadedDocId(documentId);
        setStatus("complete");
        setChunksComplete(true);
        setQaActive(false);
        onUploaded?.();
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : "Upload failed");
      } finally {
        ws.close();
      }
    },
    [onUploaded],
  );

  const reset = () => {
    setStatus("idle");
    setChunks([]);
    setFileName(null);
    setTotalExpected(null);
    setParentCount(null);
    setChunksComplete(false);
    setQaPairs([]);
    setQaExpected(null);
    setQaComplete(false);
  };

  return (
    <div className="rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-5">
      <div
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const file = e.dataTransfer.files?.[0];
          if (file) void handleFile(file);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onClick={() => inputRef.current?.click()}
        className={`ak-transition flex cursor-pointer flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed p-8 text-center ${
          dragging
            ? "border-brand bg-brand-soft/60 scale-[1.01]"
            : "border-border bg-muted/25 hover:border-brand/45 hover:bg-brand-soft/30"
        }`}
      >
        <div className="ak-transition flex h-11 w-11 items-center justify-center rounded-xl border border-border bg-card text-lg shadow-sm">
          {status === "complete" ? "✅" : status === "uploading" ? "⏳" : "📄"}
        </div>
        <p className="text-sm font-medium">{fileName ?? "Drop a document here"}</p>
        <p className="text-xs text-muted-foreground">
          PDF, DOCX, TXT or MD · or <span className="text-brand underline-offset-2">browse</span>
        </p>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleFile(file);
          }}
        />
      </div>

      {status === "uploading" && chunks.length === 0 ? (
        <p className="ak-rise mt-4 flex items-center gap-2 text-xs text-muted-foreground">
          <span className="ak-blink text-brand">●</span> Parsing document…
        </p>
      ) : null}

      {error ? (
        <p className="ak-pop mt-4 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
          {error}
        </p>
      ) : null}

      {chunks.length > 0 || chunksComplete ? (
        <div className="mt-5">
          <ChunkVisualizer
            chunks={chunks}
            totalExpected={totalExpected}
            complete={chunksComplete}
            parentCount={parentCount}
          />
        </div>
      ) : null}

      {qaPairs.length > 0 || qaActive ? (
        <div className="mt-4">
          <QaGenerationView
            pairs={qaPairs}
            expected={qaExpected}
            active={qaActive}
            complete={qaComplete}
          />
        </div>
      ) : null}

      {status === "complete" ? (
        <div className="ak-rise mt-4 flex flex-wrap items-center gap-2">
          <Link
            href={uploadedDocId ? `/chat?doc=${uploadedDocId}` : "/chat"}
            className={cn(
              buttonVariants({ size: "default" }),
              "ak-cta rounded-xl px-5 font-medium shadow-md ring-2 ring-brand/40",
            )}
          >
            💬 Chat with this document →
          </Link>
          {qaComplete ? (
            <Link
              href="/eval"
              className={cn(
                buttonVariants({ size: "sm", variant: "outline" }),
                "ak-transition rounded-lg border-brand/50",
              )}
            >
              See the RAG score →
            </Link>
          ) : null}
          <Button size="sm" variant="ghost" className="ak-transition rounded-lg" onClick={reset}>
            Upload another
          </Button>
        </div>
      ) : null}
    </div>
  );
}
