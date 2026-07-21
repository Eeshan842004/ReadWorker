export interface DocumentSummary {
  id: string;
  filename: string;
  uploaded_at: string;
  total_chunks: number;
}

export interface Source {
  id: string;
  content: string;
  document_id: string;
  score?: number;
  rrf_score?: number;
  metadata?: Record<string, unknown>;
}

export interface QueryResponse {
  answer: string;
  sources: Source[];
  model: string;
  tokens_used: number | null;
}

export interface ChunkCreatedEvent {
  type: "chunk_created";
  chunk_index: number;
  total_expected: number;
  preview: string;
  char_count: number;
}

export interface ChunkingSummaryEvent {
  type: "chunking_summary";
  parents: number;
  children: number;
}

export interface IngestCompleteEvent {
  type: "ingest_complete";
  total_chunks: number;
  parent_chunks?: number;
}

export interface QaGenerationStartEvent {
  type: "qa_generation_start";
  expected: number;
}

export interface QaGeneratedEvent {
  type: "qa_generated";
  index: number;
  total: number;
  question: string;
  answer: string;
}

export interface QaCompleteEvent {
  type: "qa_complete";
  total: number;
}

export interface QaGenerationErrorEvent {
  type: "qa_generation_error";
  message: string;
}

export type IngestWsEvent =
  | ChunkCreatedEvent
  | ChunkingSummaryEvent
  | IngestCompleteEvent
  | QaGenerationStartEvent
  | QaGeneratedEvent
  | QaCompleteEvent
  | QaGenerationErrorEvent;

export interface GeneratedQa {
  index: number;
  question: string;
  answer: string;
}

export interface EvalTestSet {
  document_id: string;
  filename: string;
  count: number;
  samples: string[];
}

export interface EvalQuestionsResponse {
  total_questions: number;
  sets: EvalTestSet[];
}

export interface UploadResponse {
  document_id: string;
  filename: string;
  total_chunks: number;
}

export interface TraceEntry {
  node: string;
  message: string;
  status?: "ok" | "warn" | "error" | "blocked";
  [key: string]: unknown;
}

export interface Citation {
  source_index: number;
  chunk_id: string;
  document_id: string;
  preview: string;
}

export interface AgenticQueryResponse {
  answer: string;
  sources: Source[];
  citations: Citation[];
  sub_questions: string[];
  rewritten_query: string;
  faithfulness_score: number | null;
  retry_count: number;
  trace_log: TraceEntry[];
  latency_ms: number;
  tokens_used: number;
  cost_usd: number;
  mode: string;
  blocked?: boolean;
  block_reason?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  trace?: TraceEntry[];
  faithfulness?: number | null;
  latencyMs?: number;
  retryCount?: number;
}

export type AgentNode =
  | "query_clarifier"
  | "planner"
  | "retriever"
  | "synthesizer"
  | "critic"
  | "guardrail_block";

export interface StreamStartEvent {
  type: "start";
  question: string;
}

export interface StreamNodeEvent {
  type: "node_complete";
  node: AgentNode;
  trace: TraceEntry[];
  faithfulness_score?: number | null;
  sub_questions?: string[] | null;
  rewritten_query?: string | null;
}

export interface StreamErrorEvent {
  type: "error";
  message: string;
}

export type StreamDoneEvent = { type: "done" } & AgenticQueryResponse;

export type StreamEvent = StreamStartEvent | StreamNodeEvent | StreamErrorEvent | StreamDoneEvent;

export interface EvalSummary {
  faithfulness?: number;
  answer_relevancy?: number;
  context_precision?: number;
  context_recall?: number;
}

export interface EvalResults {
  status: string;
  summary: EvalSummary;
  per_question: Record<string, unknown>[];
  gate?: { metric: string; threshold: number; passed: boolean };
  document_id?: string | null;
  document_name?: string | null;
  num_questions?: number;
}

export interface CostSummary {
  total_queries: number;
  total_tokens: number;
  total_cost_usd: number;
  avg_latency_ms: number;
  avg_faithfulness: number;
}
