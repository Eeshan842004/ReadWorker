"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, buttonVariants } from "@/components/ui/button";
import { clearAllDocuments, deleteDocument, listDocuments } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { DocumentSummary } from "@/lib/types";

export function DocumentList() {
  const [docs, setDocs] = useState<DocumentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    let active = true;
    (async () => {
      try {
        const result = await listDocuments();
        if (active) setDocs(result);
      } catch (err) {
        if (active) setError(err instanceof Error ? err.message : "Failed to load documents");
      } finally {
        if (active) setLoading(false);
      }
    })();
    return () => {
      active = false;
    };
  }, []);

  const remove = async (id: string) => {
    setDeleting(id);
    try {
      await deleteDocument(id);
      setDocs(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete");
    } finally {
      setDeleting(null);
    }
  };

  const clearAll = async () => {
    if (!window.confirm("Delete ALL documents and their test questions? This cannot be undone.")) {
      return;
    }
    setClearing(true);
    try {
      await clearAllDocuments();
      setDocs(await listDocuments());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to clear");
    } finally {
      setClearing(false);
    }
  };

  if (loading)
    return (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <span className="ak-blink text-brand">●</span> Loading…
      </p>
    );

  if (error)
    return (
      <p className="rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
        {error}
      </p>
    );

  if (docs.length === 0)
    return (
      <div className="ak-rise rounded-2xl border border-dashed border-border bg-card/50 p-10 text-center">
        <p className="text-sm font-medium">No documents yet</p>
        <p className="mt-1 text-xs text-muted-foreground">
          Upload one to start asking questions.
        </p>
        <Link
          href="/"
          className={cn(buttonVariants({ size: "sm" }), "ak-transition mt-4 rounded-lg")}
        >
          Upload a document
        </Link>
      </div>
    );

  const totalChunks = docs.reduce((sum, d) => sum + d.total_chunks, 0);

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-muted-foreground">
          {docs.length} document{docs.length === 1 ? "" : "s"} · {totalChunks} chunks indexed · each
          chat is grounded in one document
        </p>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => void clearAll()}
          disabled={clearing}
          className="ak-transition rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
        >
          {clearing ? "Clearing…" : "🗑 Clear everything"}
        </Button>
      </div>

      {docs.map((doc) => (
        <div
          key={doc.id}
          className="ak-rise ak-transition flex items-center justify-between gap-4 rounded-xl border border-border bg-card p-3 shadow-sm hover:border-brand/30 hover:shadow-md"
        >
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-border bg-muted/50 text-sm">
              📄
            </span>
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{doc.filename}</p>
              <p className="text-[11px] text-muted-foreground">
                <span className="font-mono">{doc.total_chunks}</span> chunks ·{" "}
                {new Date(doc.uploaded_at).toLocaleString()}
              </p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1">
            <Link
              href={`/chat?doc=${doc.id}`}
              className={cn(
                buttonVariants({ size: "sm", variant: "outline" }),
                "ak-transition rounded-lg border-brand/50 hover:-translate-y-0.5",
              )}
            >
              💬 Chat
            </Link>
            <Button
              variant="ghost"
              size="sm"
              disabled={deleting === doc.id}
              onClick={() => void remove(doc.id)}
              className="ak-transition rounded-lg text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
            >
              {deleting === doc.id ? "…" : "Delete"}
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}
