"use client";

export type ChatMode = "agentic" | "single";

const MODES: {
  id: ChatMode;
  label: string;
  tagline: string;
  detail: string;
}[] = [
  {
    id: "agentic",
    label: "Multi-agent",
    tagline: "Best answers",
    detail:
      "Clarifies → plans → retrieves → writes → fact-checks, and retries if the answer isn't grounded. Use for complex or multi-part questions. Slower (~5-30s).",
  },
  {
    id: "single",
    label: "Single-shot",
    tagline: "Fastest",
    detail:
      "One retrieval, one LLM call, no fact-checking. Use for simple lookups where you just need a quick cited answer. Fast (~1-3s).",
  },
];

export function ModeToggle({
  mode,
  onChange,
  disabled,
}: {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
  disabled?: boolean;
}) {
  const active = MODES.find((m) => m.id === mode)!;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <span className="text-xs font-medium text-muted-foreground">Answer mode</span>
        <div className="inline-flex rounded-full border border-border bg-muted/60 p-0.5">
          {MODES.map((m) => {
            const selected = m.id === mode;
            return (
              <button
                key={m.id}
                type="button"
                disabled={disabled}
                onClick={() => onChange(m.id)}
                aria-pressed={selected}
                className={`ak-transition relative rounded-full px-3.5 py-1.5 text-xs font-medium disabled:opacity-50 ${
                  selected
                    ? "bg-card text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground"
                }`}
              >
                <span className="flex items-center gap-1.5">
                  {selected ? (
                    <span className="h-1.5 w-1.5 rounded-full bg-brand" />
                  ) : null}
                  {m.label}
                </span>
              </button>
            );
          })}
        </div>
        <span className="rounded-full bg-brand-soft px-2 py-0.5 text-[10px] font-medium text-foreground">
          {active.tagline}
        </span>
      </div>
      <p className="text-[11px] leading-relaxed text-muted-foreground">{active.detail}</p>
    </div>
  );
}
