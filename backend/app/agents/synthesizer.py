from app.agents.llm import chat
from app.agents.state import AgentState, trace
from app.config import settings

_SYSTEM = """You are a research synthesizer. Create a comprehensive answer using ONLY the
provided sources. ALWAYS cite sources inline as [Source N]. If the information is
insufficient, clearly state what is missing. Be precise, factual, and well-structured.

Sources:
{context}"""


async def synthesizer(state: AgentState) -> dict:
    docs = state["reranked_documents"]
    context = "\n\n".join(
        f"[Source {i + 1}] (doc: {doc['document_id'][:8]}): {doc['content']}"
        for i, doc in enumerate(docs)
    )

    try:
        answer = await chat(
            _SYSTEM.format(context=context),
            state["rewritten_query"],
            model=settings.GROQ_SYNTHESIS_MODEL,
            temperature=0.2,
            max_tokens=2000,
        )
    except Exception as exc:
        return {
            "generation": "",
            "citations": [],
            "trace_log": [trace("synthesizer", f"LLM error: {exc}", status="error")],
        }

    citations = [
        {
            "source_index": i + 1,
            "chunk_id": doc["id"],
            "document_id": doc["document_id"],
            "preview": doc["content"][:160],
        }
        for i, doc in enumerate(docs)
    ]

    return {
        "generation": answer,
        "citations": citations,
        "trace_log": [
            trace("synthesizer", f"generated {len(answer)} chars, {len(citations)} citations", status="ok")
        ],
    }
