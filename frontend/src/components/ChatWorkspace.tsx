"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ChatInterface } from "@/components/ChatInterface";
import { ChatSidebar } from "@/components/ChatSidebar";
import {
  ChatSession,
  createSession,
  loadSessions,
  titleFromMessages,
  writeSessions,
} from "@/lib/chatStore";
import { listDocuments } from "@/lib/api";
import type { ChatMessage, DocumentSummary } from "@/lib/types";

export function ChatWorkspace() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const bootstrapped = useRef(false);

  // Bootstrap: restore history, load documents, open a draft scoped to ?doc= or the newest doc.
  useEffect(() => {
    let active = true;
    (async () => {
      const history = loadSessions();
      const docs = await listDocuments().catch(() => []);
      if (!active) return;

      const requestedId =
        typeof window !== "undefined" ? new URLSearchParams(window.location.search).get("doc") : null;
      const scoped =
        docs.find((d) => d.id === requestedId) ?? docs[0] ?? null; // ?doc= wins, else newest

      const draft = createSession(scoped?.id ?? null, scoped?.filename ?? null);
      setDocuments(docs);
      setSessions([draft, ...history]);
      setActiveId(draft.id);
      bootstrapped.current = true;
    })();
    return () => {
      active = false;
    };
  }, []);

  // Persist non-empty sessions whenever anything changes (drafts stay ephemeral).
  useEffect(() => {
    if (!bootstrapped.current) return;
    writeSessions(sessions.filter((s) => s.messages.length > 0));
  }, [sessions]);

  const setActiveMessages = useCallback(
    (updater: (prev: ChatMessage[]) => ChatMessage[]) => {
      setSessions((prev) =>
        prev.map((s) => {
          if (s.id !== activeId) return s;
          const nextMessages = updater(s.messages);
          return {
            ...s,
            messages: nextMessages,
            title: titleFromMessages(nextMessages),
            updatedAt: Date.now(),
          };
        }),
      );
    },
    [activeId],
  );

  const newChat = useCallback(
    (docId?: string | null, docName?: string | null) => {
      // Default a fresh chat to the most recent document if none specified.
      const fallback = documents[0] ?? null;
      const id = docId !== undefined ? docId : (fallback?.id ?? null);
      const name =
        docName !== undefined ? docName : (documents.find((d) => d.id === id)?.filename ?? null);
      const draft = createSession(id, name);
      setSessions((prev) => [draft, ...prev]);
      setActiveId(draft.id);
    },
    [documents],
  );

  const removeSession = useCallback(
    (id: string) => {
      const next = sessions.filter((s) => s.id !== id);
      if (id === activeId) {
        if (next.length > 0) setActiveId(next[0].id);
        else {
          const draft = createSession(documents[0]?.id ?? null, documents[0]?.filename ?? null);
          next.unshift(draft);
          setActiveId(draft.id);
        }
      }
      setSessions(next);
    },
    [sessions, activeId, documents],
  );

  // Pick which document the active chat is grounded in.
  const selectDoc = useCallback(
    (docId: string | null) => {
      const name = documents.find((d) => d.id === docId)?.filename ?? null;
      const active = sessions.find((s) => s.id === activeId);
      if (active && active.messages.length === 0) {
        // Re-scope the empty draft in place.
        setSessions((prev) =>
          prev.map((s) => (s.id === activeId ? { ...s, docId, docName: name } : s)),
        );
      } else {
        newChat(docId, name); // started chatting already → open a fresh scoped chat
      }
    },
    [documents, sessions, activeId, newChat],
  );

  const active = sessions.find((s) => s.id === activeId) ?? null;

  return (
    <div className="grid h-full grid-cols-[248px_minmax(0,1fr)] gap-4 max-lg:grid-cols-1">
      <div className="max-lg:hidden">
        <ChatSidebar
          sessions={sessions}
          activeId={activeId}
          onSelect={setActiveId}
          onNew={() => newChat()}
          onDelete={removeSession}
        />
      </div>
      <div className="min-h-0">
        {active ? (
          <ChatInterface
            key={active.id}
            messages={active.messages}
            setMessages={setActiveMessages}
            documents={documents}
            activeDocId={active.docId}
            onSelectDoc={selectDoc}
          />
        ) : null}
      </div>
    </div>
  );
}
