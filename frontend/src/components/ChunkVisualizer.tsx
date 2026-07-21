"use client";

import type { ChunkCreatedEvent } from "@/lib/types";

interface ChunkVisualizerProps {
  chunks: ChunkCreatedEvent[];
  totalExpected: number | null;
  complete: boolean;
  parentCount?: number | null;
}

export function ChunkVisualizer({
  chunks,
  totalExpected,
  complete,
  parentCount,
}: ChunkVisualizerProps) {
  if (chunks.length === 0 && !complete) return null;

  const progress = totalExpected ? Math.min(100, (chunks.length / totalExpected) * 100) : null;

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-sm">
          {complete ? (
            <span className="flex h-4 w-4 items-center justify-center rounded-full bg-success/15 text-[9px] text-success">
              ✓
            </span>
          ) : (
            <span className="ak-blink text-brand">●</span>
          )}
          <span className="font-medium">
            {complete ? "Embedded & indexed" : "Chunking + embedding…"}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-[11px]">
          {parentCount ? (
            <span className="rounded-full bg-muted px-2 py-0.5 font-mono text-muted-foreground">
              {parentCount} parents
            </span>
          ) : null}
          <span className="rounded-full bg-brand-soft px-2 py-0.5 font-mono font-medium text-foreground">
            {chunks.length}
            {totalExpected ? ` / ${totalExpected}` : ""} chunks
          </span>
        </div>
      </div>

      <div className="h-1 w-full overflow-hidden rounded-full bg-muted">
        <div
          className={`h-full rounded-full transition-[width] duration-300 ease-out ${
            complete ? "bg-success" : "bg-brand"
          }`}
          style={{ width: progress !== null ? `${progress}%` : complete ? "100%" : "35%" }}
        />
      </div>

      <div className="grid max-h-80 grid-cols-1 gap-2 overflow-y-auto pr-1 sm:grid-cols-2">
        {chunks.map((chunk) => (
          <div
            key={chunk.chunk_index}
            className="ak-rise ak-transition rounded-lg border border-border bg-card p-2.5 hover:border-brand/35 hover:shadow-sm"
          >
            <div className="mb-1 flex items-center justify-between text-[10px] text-muted-foreground">
              <span className="font-mono font-medium text-brand">#{chunk.chunk_index}</span>
              <span className="font-mono">{chunk.char_count} chars</span>
            </div>
            <p className="line-clamp-3 text-[11px] leading-relaxed text-foreground/75">
              {chunk.preview}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
