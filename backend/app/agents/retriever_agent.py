import asyncio

from app.agents.state import AgentState, trace
from app.retrieval.reranker import reranker
from app.retrieval.service import retrieve


async def retriever_agent(state: AgentState) -> dict:
    """Hybrid-retrieve for every sub-question, dedupe, then rerank.

    Sub-questions are independent (each is an embedding call + a DB query), so they run
    concurrently; gather preserves input order, keeping dedup results deterministic.
    On a critic-triggered retry we widen the candidate pool so re-retrieval can actually
    surface new evidence instead of returning the identical set.
    """
    retry = state.get("retry_count", 0)
    per_q_top_k = 5 + retry * 3  # widen on retry
    rerank_top_k = 7
    document_ids = state.get("document_ids") or None

    per_question_results = await asyncio.gather(
        *(
            retrieve(sub_q, top_k=per_q_top_k, expand_parents=True, document_ids=document_ids)
            for sub_q in state["sub_questions"]
        )
    )
    all_docs: list[dict] = [doc for results in per_question_results for doc in results]

    seen: set[str] = set()
    unique_docs = []
    for doc in all_docs:
        if doc["id"] not in seen:
            seen.add(doc["id"])
            unique_docs.append(doc)

    try:
        reranked = await reranker.rerank(state["rewritten_query"], unique_docs, top_k=rerank_top_k)
    except Exception:
        reranked = unique_docs[:rerank_top_k]

    return {
        "retrieved_documents": unique_docs,
        "reranked_documents": reranked,
        "trace_log": [
            trace(
                "retriever",
                f"found {len(unique_docs)} unique chunks, reranked to {len(reranked)}"
                + (f" (retry {retry}, wider pool)" if retry else ""),
                status="ok",
            )
        ],
    }
