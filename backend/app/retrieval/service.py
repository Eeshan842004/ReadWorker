"""High-level retrieval facade shared by the agent pipeline, the /query endpoint,
and the MCP server. Handles query embedding, hybrid retrieval, and (for parent-child
chunking) swapping matched child chunks for their richer parent content."""

from app.ingestion.embedder import embedding_service
from app.retrieval.hybrid_retriever import hybrid_retriever


def expand_to_parents(chunks: list[dict]) -> list[dict]:
    """Replace child content with parent content when available (small-to-big)."""
    expanded = []
    seen_parents: set[str] = set()
    for chunk in chunks:
        meta = chunk.get("metadata") or {}
        parent_id = meta.get("parent_chunk_id")
        parent_content = meta.get("parent_content")
        if parent_id and parent_content:
            if parent_id in seen_parents:
                continue
            seen_parents.add(parent_id)
            expanded.append({**chunk, "content": parent_content, "expanded_from_child": True})
        else:
            expanded.append(chunk)
    return expanded


async def retrieve(
    query: str,
    top_k: int = 5,
    expand_parents: bool = True,
    document_ids: list[str] | None = None,
) -> list[dict]:
    query_embedding = await embedding_service.embed_query(query)
    results = await hybrid_retriever.retrieve(
        query, query_embedding, top_k=top_k, document_ids=document_ids
    )
    return expand_to_parents(results) if expand_parents else results
