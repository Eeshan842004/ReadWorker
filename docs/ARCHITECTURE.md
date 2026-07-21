# Architecture

## System overview

```mermaid
flowchart TB
    subgraph Frontend [Next.js 16 App Router]
        UP[Upload + live ChunkVisualizer]
        CH[Chat: single-shot / multi-agent]
        EV[Eval dashboard - recharts]
        TR[Trace viewer]
    end

    subgraph Backend [FastAPI]
        ING[/ingest/upload/]
        WS[(WebSocket /ws/ingest)]
        Q1[/query - single-shot/]
        Q2[/query/agentic - multi-agent/]
        EVR[/eval/*/]
        AUTH[/auth/*/ JWT]
    end

    subgraph Pipeline [LangGraph multi-agent]
        CL[Query Clarifier + guardrails] --> PL[Planner]
        PL --> RT[Retriever agent]
        RT --> SY[Synthesizer]
        SY --> CR[Critic / faithfulness]
        CR -.re-retrieve.-> RT
    end

    subgraph Retrieval
        DE[Dense - pgvector cosine]
        SP[Sparse - BM25]
        HY[Hybrid RRF] --> RR[LLM reranker]
    end

    UP --> ING --> WS --> UP
    ING --> EMB[Gemini embeddings] --> PG[(PostgreSQL + pgvector)]
    CH --> Q2 --> Pipeline
    RT --> HY
    DE --> PG
    SY --> GROQ[Groq llama-3.3-70b]
    CR --> GROQ8[Groq llama-3.1-8b]
    EV --> EVR --> RAGAS[ragas + Groq judge]

    MCP[MCP server :8421] --> Retrieval
    MCP --> Pipeline
```

## Request lifecycle (multi-agent query)

1. **TraceIDMiddleware** assigns an `X-Trace-Id`, bound into structlog context.
2. **Query Clarifier** runs input guardrails (prompt-injection block, PII redaction) and
   rewrites the query with the fast 8B model. A tripped guardrail short-circuits to a
   terminal `guardrail_block` node.
3. **Planner** decomposes into 1–3 sub-questions (70B, JSON mode).
4. **Retriever agent** hybrid-retrieves per sub-question (dense pgvector + BM25 fused via
   RRF), expands matched child chunks to their parents (small-to-big), dedupes, and
   reranks with the 8B LLM reranker. On a critic-triggered retry it widens the pool.
5. **Synthesizer** composes a cited answer (70B) using only retrieved context.
6. **Critic** scores faithfulness (8B, JSON). Below 0.7 and under the retry cap → loop back
   to the retriever; otherwise finish.
7. **Cost tracker** persists tokens/latency/faithfulness to `query_logs`.

## Key design decisions

- **Partial-state node returns.** Each LangGraph node returns only the keys it changed
  (not `{**state, ...}`), which is idiomatic and avoids double-appending to the
  `trace_log` reducer.
- **Lazy external clients.** Groq and Gemini clients are constructed on first use so the
  app boots and imports without any API keys — keys are only needed at request time.
- **Graceful observability.** Langfuse `@observe` is a no-op decorator unless keys are set.
- **MCP isolation.** `fastmcp` needs a newer `starlette` than FastAPI 0.115 allows, so the
  MCP server runs as its own process/container with `requirements-mcp.txt`.

## Data model

- `documents` — one row per uploaded file (`total_chunks`, metadata).
- `chunks` — child chunks with a `Vector(3072)` embedding, `parent_chunk_id`, and parent
  content in metadata for small-to-big retrieval.
- `users` — JWT auth (bcrypt-hashed passwords).
- `query_logs` — per-request tokens, cost, latency, faithfulness, trace id.
