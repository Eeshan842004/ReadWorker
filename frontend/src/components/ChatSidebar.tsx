"use client";

import type { ChatSession } from "@/lib/chatStore";

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export function ChatSidebar({
  sessions,
  activeId,
  onSelect,
  onNew,
  onDelete,
}: {
  sessions: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
}) {
  return (
    <aside className="flex h-full flex-col gap-3">
      <button
        onClick={onNew}
        className="ak-transition flex items-center justify-center gap-2 rounded-xl border border-brand/50 bg-brand-soft px-3 py-2.5 text-sm font-medium text-foreground hover:-translate-y-0.5 hover:shadow-sm"
      >
        <span className="text-brand">＋</span> New chat
      </button>

      <div className="flex-1 space-y-1 overflow-y-auto pr-1">
        {sessions.length === 0 ? (
          <p className="px-2 pt-4 text-center text-xs text-muted-foreground">
            Your chats will appear here.
          </p>
        ) : (
          sessions.map((s) => {
            const active = s.id === activeId;
            return (
              <div
                key={s.id}
                onClick={() => onSelect(s.id)}
                className={`ak-transition group cursor-pointer rounded-lg border px-2.5 py-2 ${
                  active
                    ? "border-brand/50 bg-card shadow-sm"
                    : "border-transparent hover:border-border hover:bg-card/60"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="line-clamp-1 text-[13px] font-medium text-foreground">{s.title}</p>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDelete(s.id);
                    }}
                    aria-label="Delete chat"
                    className="ak-transition shrink-0 text-muted-foreground opacity-0 hover:text-destructive group-hover:opacity-100"
                  >
                    ✕
                  </button>
                </div>
                <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-muted-foreground">
                  <span>{relativeTime(s.updatedAt)}</span>
                  {s.docName ? (
                    <>
                      <span>·</span>
                      <span className="line-clamp-1">📎 {s.docName}</span>
                    </>
                  ) : null}
                </div>
              </div>
            );
          })
        )}
      </div>
    </aside>
  );
}
