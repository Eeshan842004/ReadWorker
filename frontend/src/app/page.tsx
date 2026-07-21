import { UploadPanel } from "@/components/UploadPanel";

const STEPS = [
  { n: "1", t: "Split", d: "Parent + child chunks" },
  { n: "2", t: "Embed", d: "Gemini, 3072-dim vectors" },
  { n: "3", t: "Index", d: "pgvector + BM25" },
];

export default function HomePage() {
  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-card px-2.5 py-1 text-[11px] font-medium text-muted-foreground shadow-sm">
          <span className="h-1.5 w-1.5 rounded-full bg-success" />
          Zero API cost · Groq + Gemini free tier
        </span>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Upload a document, watch it think.
        </h1>
        <p className="max-w-xl text-sm leading-relaxed text-muted-foreground">
          Your file is split, embedded, and indexed live — every chunk appears below as it&apos;s
          created. Then ask questions and get answers grounded in your own documents, with
          citations.
        </p>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {STEPS.map((s) => (
          <div key={s.n} className="rounded-xl border border-border bg-card p-3 shadow-sm">
            <div className="mb-1 flex h-5 w-5 items-center justify-center rounded-md bg-brand-soft font-mono text-[10px] font-semibold text-foreground">
              {s.n}
            </div>
            <p className="text-xs font-medium">{s.t}</p>
            <p className="text-[11px] text-muted-foreground">{s.d}</p>
          </div>
        ))}
      </div>

      <UploadPanel />
    </div>
  );
}
