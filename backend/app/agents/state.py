from operator import add
from typing import Annotated, TypedDict


class AgentState(TypedDict, total=False):
    question: str                          # Original user question
    rewritten_query: str                   # Clarified / rewritten query
    sub_questions: list[str]               # Decomposed sub-questions
    retrieved_documents: list[dict]        # Retrieved chunks (deduped)
    reranked_documents: list[dict]         # After reranking
    generation: str                        # Synthesized answer
    citations: list[dict]                  # Source citations
    faithfulness_score: float              # Critic's assessment
    needs_re_retrieval: bool               # Critic flag
    retry_count: int                       # Prevent infinite loops
    blocked: bool                          # Guardrail tripped
    block_reason: str                      # Why the request was blocked
    document_ids: list[str]                # Restrict retrieval to these docs (empty = all)
    trace_log: Annotated[list[dict], add]  # Append-only structured trace
    conversation_history: list[dict]       # Rolling conversation memory


def initial_state(
    question: str,
    conversation_history: list[dict] | None = None,
    document_ids: list[str] | None = None,
) -> AgentState:
    return {
        "question": question,
        "rewritten_query": "",
        "sub_questions": [],
        "retrieved_documents": [],
        "reranked_documents": [],
        "generation": "",
        "citations": [],
        "faithfulness_score": 0.0,
        "needs_re_retrieval": False,
        "retry_count": 0,
        "blocked": False,
        "block_reason": "",
        "document_ids": document_ids or [],
        "trace_log": [],
        "conversation_history": conversation_history or [],
    }


def trace(node: str, message: str, **extra) -> dict:
    """Build one structured trace entry (consumed by the frontend trace viewer)."""
    return {"node": node, "message": message, **extra}
