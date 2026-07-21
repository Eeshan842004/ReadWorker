"use client";

import { useEffect, useRef, useState } from "react";

import type { DocumentSummary } from "@/lib/types";

/**
 * Searchable document picker. Shows the current document; opening it reveals a search
 * box + filtered list. Selecting a document scopes retrieval to it.
 */
export function DocumentSelect({
  documents,
  value,
  onChange,
  disabled,
}: {
  documents: DocumentSummary[];
  value: string | null;
  onChange: (docId: string | null) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [open]);

  const current = documents.find((d) => d.id === value);
  const label = current ? current.filename : "All documents";

  const filtered = query
    ? documents.filter((d) => d.filename.toLowerCase().includes(query.toLowerCase()))
    : documents;

  const pick = (docId: string | null) => {
    onChange(docId);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={rootRef} className="relative">
      <button
        type="button"
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
        className="ak-transition flex max-w-[260px] items-center gap-1.5 rounded-full border border-brand/40 bg-brand-soft px-2.5 py-1 text-[11px] font-medium text-foreground hover:border-brand/60 disabled:opacity-70"
        title={disabled ? "Start a new chat to switch documents" : "Choose a document"}
      >
        <span className="truncate">{label}</span>
        <span className={`transition-transform ${open ? "rotate-180" : ""}`}>▾</span>
      </button>

      {open ? (
        <div className="ak-pop absolute z-40 mt-1 w-72 overflow-hidden rounded-xl border border-border bg-popover shadow-lg">
          <div className="border-b border-border p-2">
            <input
              autoFocus
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search documents…"
              className="w-full rounded-lg border border-border bg-card px-2.5 py-1.5 text-[12px] focus-visible:border-brand/60 focus-visible:outline-none"
            />
          </div>
          <div className="max-h-60 overflow-y-auto p-1">
            <button
              onClick={() => pick(null)}
              className={`ak-transition flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[12px] hover:bg-accent ${
                value === null ? "font-medium text-foreground" : "text-muted-foreground"
              }`}
            >
              <span>🗂️</span> All documents
            </button>
            {filtered.map((d) => (
              <button
                key={d.id}
                onClick={() => pick(d.id)}
                className={`ak-transition flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left text-[12px] hover:bg-accent ${
                  value === d.id ? "font-medium text-foreground" : "text-muted-foreground"
                }`}
              >
                <span>📄</span>
                <span className="truncate">{d.filename}</span>
                {value === d.id ? <span className="ml-auto text-brand">✓</span> : null}
              </button>
            ))}
            {filtered.length === 0 ? (
              <p className="px-2.5 py-2 text-[11px] text-muted-foreground">No matches.</p>
            ) : null}
          </div>
        </div>
      ) : null}
    </div>
  );
}
