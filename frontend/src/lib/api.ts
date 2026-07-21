import type {
  AgenticQueryResponse,
  CostSummary,
  DocumentSummary,
  EvalQuestionsResponse,
  EvalResults,
  QueryResponse,
  StreamEvent,
  UploadResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/** Shared fetch wrapper: throws `<label>: <statusText>` on non-2xx, parses JSON otherwise. */
async function fetchJson<T>(path: string, label: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, init);
  if (!res.ok) throw new Error(`${label}: ${res.statusText}`);
  return res.json();
}

function postJson<T>(path: string, label: string, body: unknown): Promise<T> {
  return fetchJson<T>(path, label, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function ingestWsUrl(documentId: string): string {
  return `${API_URL.replace(/^http/, "ws")}/ws/ingest/${documentId}`;
}

export function uploadDocument(file: File, documentId: string): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return fetchJson(`/ingest/upload?document_id=${documentId}`, "Upload failed", {
    method: "POST",
    body: formData,
  });
}

export function askQuestion(
  question: string,
  topK = 5,
  documentIds: string[] = [],
): Promise<QueryResponse> {
  return postJson("/query", "Query failed", {
    question,
    top_k: topK,
    document_ids: documentIds,
  });
}

export function askAgentic(
  question: string,
  conversationHistory: { role: string; content: string }[] = [],
  documentIds: string[] = [],
): Promise<AgenticQueryResponse> {
  return postJson("/query/agentic", "Agentic query failed", {
    question,
    conversation_history: conversationHistory,
    document_ids: documentIds,
  });
}

/**
 * Streams the multi-agent pipeline over SSE, invoking `onEvent` as each agent node
 * finishes. Uses fetch + ReadableStream rather than EventSource because EventSource
 * cannot issue POST requests.
 */
export async function askAgenticStream(
  question: string,
  onEvent: (event: StreamEvent) => void,
  conversationHistory: { role: string; content: string }[] = [],
  documentIds: string[] = [],
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${API_URL}/query/agentic/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      conversation_history: conversationHistory,
      document_ids: documentIds,
    }),
    signal,
  });

  if (!res.ok || !res.body) throw new Error(`Stream failed: ${res.status} ${res.statusText}`);

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    // SSE frames are separated by a blank line.
    const frames = buffer.split("\n\n");
    buffer = frames.pop() ?? "";

    for (const frame of frames) {
      const line = frame.split("\n").find((l) => l.startsWith("data: "));
      if (!line) continue;
      try {
        onEvent(JSON.parse(line.slice(6)) as StreamEvent);
      } catch {
        // ignore malformed frame
      }
    }
  }
}

export function getEvalResults(): Promise<EvalResults> {
  return fetchJson("/eval/results", "Failed to load eval results");
}

export function runEval(documentId?: string): Promise<{ status: string }> {
  const qs = documentId ? `?document_id=${encodeURIComponent(documentId)}` : "";
  return fetchJson(`/eval/run${qs}`, "Failed to start eval", { method: "POST" });
}

export function getEvalStatus(): Promise<{ in_progress: boolean }> {
  return fetchJson("/eval/status", "Failed to load eval status");
}

export function getEvalQuestions(): Promise<EvalQuestionsResponse> {
  return fetchJson("/eval/questions", "Failed to load test sets");
}

export function getCostSummary(): Promise<CostSummary> {
  return fetchJson("/eval/cost", "Failed to load cost summary");
}

export function listDocuments(): Promise<DocumentSummary[]> {
  return fetchJson("/documents", "Failed to list documents");
}

export async function deleteDocument(documentId: string): Promise<void> {
  const res = await fetch(`${API_URL}/documents/${documentId}`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to delete document: ${res.statusText}`);
}

export async function clearAllDocuments(): Promise<void> {
  const res = await fetch(`${API_URL}/documents`, { method: "DELETE" });
  if (!res.ok) throw new Error(`Failed to clear documents: ${res.statusText}`);
}
