import pytest

from app.ingestion.chunker import DocumentChunker
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.sparse_retriever import SparseRetriever

SAMPLE_TEXT = (
    "Photosynthesis converts sunlight into chemical energy in plants. "
    "Mitochondria are the powerhouse of the cell and produce ATP. "
    "The water cycle involves evaporation, condensation, and precipitation. "
    "Newton formulated three laws of motion describing force and acceleration. "
    "DNA carries genetic information encoded in nucleotide sequences. "
) * 4


@pytest.mark.asyncio
async def test_chunker_emits_ws_event_per_chunk():
    chunker = DocumentChunker(chunk_size=120, chunk_overlap=20)
    events: list[dict] = []

    async def callback(event: dict) -> None:
        events.append(event)

    chunks = await chunker.chunk_document(SAMPLE_TEXT, "doc1", ws_callback=callback)

    assert len(chunks) > 1
    assert len(events) == len(chunks)
    assert all(e["type"] == "chunk_created" for e in events)


async def _build_sparse() -> tuple[SparseRetriever, list[dict]]:
    chunker = DocumentChunker(chunk_size=120, chunk_overlap=20)
    chunks = await chunker.chunk_document(SAMPLE_TEXT, "doc1")
    docs = [
        {"id": c["id"], "content": c["content"], "document_id": "doc1", "metadata": {}} for c in chunks
    ]
    sparse = SparseRetriever()
    await sparse.build_index(docs)
    return sparse, docs


@pytest.mark.asyncio
async def test_bm25_returns_relevant_hits():
    sparse, _ = await _build_sparse()
    results = await sparse.retrieve("genetic information DNA nucleotide", top_k=3)
    assert results
    assert results[0]["score"] > 0


@pytest.mark.asyncio
async def test_hybrid_rrf_fuses_dense_and_sparse():
    sparse, docs = await _build_sparse()

    class FakeDense:
        async def retrieve(self, embedding, top_k=10, document_ids=None):
            return [{**docs[0], "score": 0.9}]

    hybrid = HybridRetriever(FakeDense(), sparse)
    fused = await hybrid.retrieve("DNA", [0.0] * 3, top_k=3)

    assert fused
    assert "rrf_score" in fused[0]
