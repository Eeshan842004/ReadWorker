"""Business logic for the MCP tools, kept import-light and framework-agnostic so it can
be unit-tested and reused by the FastMCP server."""

import json

from app.agents.graph import run_pipeline
from app.database.connection import get_session
from app.database.models import Document
from app.retrieval.service import retrieve
from sqlalchemy import select


async def search_documents_impl(query: str, top_k: int = 5) -> str:
    results = await retrieve(query, top_k=top_k)
    return json.dumps(
        [
            {
                "content": r["content"][:500],
                "score": r.get("rrf_score", r.get("score", 0)),
                "document_id": r["document_id"],
            }
            for r in results
        ]
    )


async def ask_knowledge_worker_impl(question: str) -> str:
    state = await run_pipeline(question)
    return json.dumps(
        {
            "answer": state.get("generation", ""),
            "faithfulness": state.get("faithfulness_score"),
            "sources_used": len(state.get("citations", [])),
        }
    )


async def list_documents_impl() -> str:
    async with get_session() as session:
        result = await session.execute(select(Document))
        docs = result.scalars().all()
        return json.dumps(
            [{"id": d.id, "filename": d.filename, "total_chunks": d.total_chunks} for d in docs]
        )
