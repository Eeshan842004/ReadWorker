# Trade-offs, limitations & what broke

Honest engineering notes. This is the maturity signal — the system has real seams.

## What broke during the build

- **Dependency hell between the MCP and API stacks.** Installing `fastmcp` and
  `langgraph`/`langchain` 1.x silently upgraded `starlette` to 1.x (breaks FastAPI 0.115,
  which raised `Router.__init__() got an unexpected keyword argument 'on_startup'`) and
  `langchain-core` to 1.x (breaks `langchain-google-genai` 2.x, which needs core <0.4).
  **Resolution:** pinned the API to the langchain 0.3-era stack + `langgraph` 0.2.x, and
  moved `fastmcp` into a separate `requirements-mcp.txt` so the MCP server runs in its own
  environment. Documented the pins with a "do not bump" note in `requirements.txt`.
- **BM25 returns nothing on homogeneous corpora.** If a term appears in every chunk its IDF
  collapses to ~0, and the `score > 0` filter drops everything. Surfaced first as a false
  test failure with repeated filler text; fixed the test data, kept the filter (correct
  behavior).
- **Eager client construction crashed boot.** The original embedder/Groq clients were built
  at import time and blew up without credentials. Made them lazy (`cached_property` /
  `lru_cache`).
- **Raw SQL couldn't express the pgvector cast.** The dense retriever used
  `text("... embedding <=> :query_vec::vector ...")`. SQLAlchemy's bind-parameter parser
  collides with Postgres' `::` cast operator, so `:query_vec` was never bound and every
  query died with `syntax error at or near ":"`. Only surfaced once a real database was
  attached — import tests can't catch it. **Resolution:** dropped the raw SQL for pgvector's
  SQLAlchemy integration (`Chunk.embedding.cosine_distance(...)`), which is type-safe and
  needs no cast.
- **Gemini rejected the embedding model name.** `gemini-embedding-001` returns
  `400 unexpected model name format`; the API requires the fully-qualified
  `models/gemini-embedding-001`. Would have broken all ingestion in production.
- **passlib is dead and breaks modern bcrypt.** `passlib` 1.7.4 (last release 2020) raises a
  spurious `password cannot be longer than 72 bytes` on an 11-byte password when running
  against `bcrypt` 5.x. **Resolution:** dropped passlib, call `bcrypt` directly.
- **Hard-coded CORS origin broke the whole UI.** The API allowed only
  `http://localhost:3000`. When port 3000 was already occupied, Next.js silently started on
  3001, so every browser call failed the CORS preflight with a 400 and surfaced as an opaque
  `Failed to fetch` — while `curl` (which sends no `Origin`) worked perfectly, making it look
  like a frontend bug. **Resolution:** development now allows any `localhost`/`127.0.0.1`
  port via `allow_origin_regex`; production still uses an explicit `CORS_ORIGINS` allowlist.
  Lesson: testing an API with curl does not test the browser's CORS path.
- **Groq's free tier has a hard daily token cap.** `llama-3.3-70b-versatile` is limited to
  100k tokens/day (TPD), separate from per-minute limits. Once exhausted, every synthesis
  call 429s and the pipeline returns empty answers. **Resolution:** the shared `chat()`
  helper now retries transient (per-minute) limits with exponential backoff, and on a
  *daily* cap immediately falls back 70B → 8B (which has its own budget) rather than
  failing. Fallbacks are surfaced in the API response as `model_fallbacks`.

## Known limitations

- **In-memory BM25 index.** Rebuilt from the full `chunks` table on every upload and on
  startup. Fine for a demo corpus; doesn't scale or survive multi-worker deployments.
  A production version would use Postgres full-text search or a dedicated sparse index.
- **Re-retrieval loop is shallow.** On a low faithfulness score the retriever widens its
  candidate pool, but it does not reformulate the query, so a genuinely unanswerable
  question just burns the retry budget (capped at 2).
- **LLM-as-reranker latency.** Reranking issues one 8B call per candidate (bounded to 15).
  Accurate and free, but adds latency; a local cross-encoder (`flashrank`) would be faster.
- **Guardrails are regex-based.** Prompt-injection and PII detection catch obvious cases
  only; they are not a substitute for a real moderation layer.
- **Auth is optional by design.** Endpoints resolve a user when a JWT is present but don't
  require one, to keep the demo frictionless. Flip `get_current_user_optional` →
  `get_current_user` to lock them down.
- **Rate limiting is per-IP** (slowapi in-memory), so it resets on restart and isn't shared
  across replicas. Redis-backed limiting is the production path.
- **Cost tracker assumes free tier** ($0). The formula is real; only the price constant is
  zero.
- **Answer quality degrades on 8B fallback.** When the 70B daily cap is hit, synthesis falls
  back to `llama-3.1-8b-instant`. Answers stay grounded and cited, but measured faithfulness
  drops (~0.75 vs the 0.9 target) and the critic burns more re-retrieval retries. The
  fallback trades quality for availability — the alternative is a hard failure. Any eval run
  should be done on a fresh daily budget, or the numbers will understate the 70B pipeline.

## Things tried and abandoned

- **Single-file `DocumentChunker` for parents+children** — replaced with a dedicated
  `ParentChildChunker` returning `(parents, children)` because embedding parents too was
  wasteful; only children are embedded/indexed.
- **`{**state, ...}` node returns** (as in the original plan) — abandoned for partial
  returns to avoid re-appending the whole `trace_log` through the `add` reducer.

## What I'd do next

1. Persist BM25 / move to Postgres FTS.
2. Add query reformulation to the re-retrieval loop.
3. Swap the LLM reranker for `flashrank` and A/B the quality/latency.
4. Redis-backed rate limiting + per-user quotas.
5. Real eval corpus (50+ golden pairs) and wire the CI gate to block on regressions.
