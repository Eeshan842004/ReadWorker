import type { ChatMessage } from "./types";

/**
 * Browser-local chat history. Sessions live in localStorage (no chat-session backend),
 * so history persists per browser across reloads. Each session is scoped to ONE document
 * — retrieval for that chat is restricted to it, and it shows as the "Grounded in" chip.
 */

const STORAGE_KEY = "akw.chat.sessions.v2";

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  docId: string | null;
  docName: string | null;
  createdAt: number;
  updatedAt: number;
}

function safeParse(raw: string | null): ChatSession[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function loadSessions(): ChatSession[] {
  if (typeof window === "undefined") return [];
  return safeParse(window.localStorage.getItem(STORAGE_KEY)).sort(
    (a, b) => b.updatedAt - a.updatedAt,
  );
}

function persist(sessions: ChatSession[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

/** Overwrite the whole stored list (callers pass only sessions worth keeping). */
export function writeSessions(sessions: ChatSession[]): void {
  persist(sessions);
}

export function createSession(docId: string | null = null, docName: string | null = null): ChatSession {
  const now = Date.now();
  return {
    id: crypto.randomUUID(),
    title: "New chat",
    messages: [],
    docId,
    docName,
    createdAt: now,
    updatedAt: now,
  };
}

export function deleteSession(id: string): ChatSession[] {
  const next = loadSessions().filter((s) => s.id !== id);
  persist(next);
  return next;
}

/** Derive a short title from the first user message. */
export function titleFromMessages(messages: ChatMessage[]): string {
  const firstUser = messages.find((m) => m.role === "user");
  if (!firstUser) return "New chat";
  const text = firstUser.content.trim().replace(/\s+/g, " ");
  return text.length > 42 ? `${text.slice(0, 42)}…` : text;
}
