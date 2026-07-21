import json
import time
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.graph import agent_pipeline, run_pipeline
from app.agents.llm import chat, get_fallback_events, get_token_usage, reset_token_usage, route_model
from app.agents.state import initial_state
from app.auth.dependencies import get_current_user_optional
from app.config import settings
from app.database.models import User
from app.observability.cost_tracker import estimate_cost, log_query
from app.observability.logging import current_trace_id, get_logger
from app.rate_limit import limiter
from app.retrieval.service import retrieve

router = APIRouter()
log = get_logger("query")


class QueryRequest(BaseModel):
    question: str
    top_k: int = settings.DEFAULT_TOP_K
    document_ids: list[str] = []


class AgenticQueryRequest(BaseModel):
    question: str
    conversation_history: list[dict] = []
    document_ids: list[str] = []


@router.post("/query")
@limiter.limit("30/minute")
async def query(
    request: Request,
    body: QueryRequest,
    user: User | None = Depends(get_current_user_optional),
):
    """Single-shot RAG (Phase 1): hybrid retrieve → one Groq call."""
    reset_token_usage()
    results = await retrieve(body.question, top_k=body.top_k, document_ids=body.document_ids or None)

    context = "\n\n".join(f"[Source {i + 1}]: {r['content']}" for i, r in enumerate(results))
    model = route_model(body.question)

    answer = await chat(
        system=(
            "You are a research assistant. Answer using ONLY the provided context. "
            "Cite sources as [Source N]. If you cannot answer from the context, say so.\n\n"
            "Context:\n" + context
        ),
        user=body.question,
        model=model,
        temperature=0.1,
        max_tokens=1500,
    )
    usage = get_token_usage()

    await log_query(
        question=body.question,
        answer=answer or "",
        model=model,
        token_usage=usage,
        latency_ms=0.0,
        trace_id=current_trace_id(),
        user_id=user.id if user else None,
    )

    return {
        "answer": answer,
        "sources": results,
        "model": model,
        "tokens_used": usage["total"],
        "cost_usd": estimate_cost(usage["total"]),
        "model_fallbacks": get_fallback_events(),
        "mode": "single_shot",
    }


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, default=str)}\n\n"


# Reducer keys accumulate across node updates; everything else is last-write-wins.
_APPEND_KEYS = {"trace_log"}


def _agentic_payload(state: dict, usage: dict, latency_ms: float, fallbacks: list) -> dict:
    """Response body shared by the SSE `done` frame and the blocking agentic endpoint."""
    return {
        "answer": state.get("generation", ""),
        "sources": state.get("reranked_documents", []),
        "citations": state.get("citations", []),
        "sub_questions": state.get("sub_questions", []),
        "rewritten_query": state.get("rewritten_query", ""),
        "faithfulness_score": state.get("faithfulness_score"),
        "retry_count": state.get("retry_count", 0),
        "trace_log": state.get("trace_log", []),
        "latency_ms": latency_ms,
        "tokens_used": usage.get("total", 0),
        "cost_usd": estimate_cost(usage.get("total", 0)),
        "model_fallbacks": fallbacks,
        "mode": "agentic",
    }


async def _log_agentic_query(
    question: str, state: dict, usage: dict, latency_ms: float, user: User | None
) -> None:
    await log_query(
        question=question,
        answer=state.get("generation", ""),
        model=settings.GROQ_SYNTHESIS_MODEL,
        token_usage=usage,
        latency_ms=latency_ms,
        trace_id=current_trace_id(),
        user_id=user.id if user else None,
        faithfulness_score=state.get("faithfulness_score"),
    )


@router.post("/query/agentic/stream")
@limiter.limit("15/minute")
async def agentic_query_stream(
    request: Request,
    body: AgenticQueryRequest,
    user: User | None = Depends(get_current_user_optional),
):
    """Same pipeline as /query/agentic, but emits Server-Sent Events as each agent node
    finishes so the UI can show live progress instead of a blind spinner."""

    async def events() -> AsyncIterator[str]:
        reset_token_usage()
        start = time.perf_counter()
        state: dict = {}

        yield _sse({"type": "start", "question": body.question})

        try:
            async for chunk in agent_pipeline.astream(
                initial_state(body.question, body.conversation_history, body.document_ids or None),
                stream_mode="updates",
            ):
                for node, update in chunk.items():
                    if not isinstance(update, dict):
                        continue
                    for key, value in update.items():
                        if key in _APPEND_KEYS:
                            state.setdefault(key, [])
                            state[key] = state[key] + list(value or [])
                        else:
                            state[key] = value

                    yield _sse(
                        {
                            "type": "node_complete",
                            "node": node,
                            "trace": list(update.get("trace_log", []) or []),
                            "faithfulness_score": update.get("faithfulness_score"),
                            "sub_questions": update.get("sub_questions"),
                            "rewritten_query": update.get("rewritten_query"),
                        }
                    )
        except Exception as exc:  # surface pipeline failures to the client
            yield _sse({"type": "error", "message": f"{type(exc).__name__}: {exc}"})
            return

        latency_ms = round((time.perf_counter() - start) * 1000, 1)
        usage = get_token_usage()

        try:
            await _log_agentic_query(body.question, state, usage, latency_ms, user)
        except Exception as exc:
            log.warning("cost_log_failed", error=str(exc))

        yield _sse(
            {
                "type": "done",
                **_agentic_payload(state, usage, latency_ms, get_fallback_events()),
                "blocked": state.get("blocked", False),
                "block_reason": state.get("block_reason", ""),
            }
        )

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/query/agentic")
@limiter.limit("15/minute")
async def agentic_query(
    request: Request,
    body: AgenticQueryRequest,
    user: User | None = Depends(get_current_user_optional),
):
    """Full multi-agent pipeline (Phase 3): clarifier → planner → retriever → synthesizer → critic."""
    state = await run_pipeline(body.question, body.conversation_history, body.document_ids or None)

    if state.get("blocked"):
        return {
            "answer": state.get("generation", ""),
            "blocked": True,
            "block_reason": state.get("block_reason", ""),
            "trace_log": state.get("trace_log", []),
            "mode": "agentic",
        }

    usage = state.get("token_usage", get_token_usage())
    latency_ms = state.get("latency_ms", 0.0)
    await _log_agentic_query(body.question, state, usage, latency_ms, user)

    return _agentic_payload(state, usage, latency_ms, state.get("model_fallbacks", []))
