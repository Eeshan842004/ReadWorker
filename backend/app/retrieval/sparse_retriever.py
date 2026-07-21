import asyncio

import numpy as np
from rank_bm25 import BM25Okapi


class SparseRetriever:
    """In-memory BM25 index.

    Tokenizing, index construction, and scoring are pure CPU — run them in a worker
    thread so they never stall the event loop while other requests are in flight.
    """

    def __init__(self):
        self.bm25: BM25Okapi | None = None
        self.chunks: list[dict] = []

    async def build_index(self, chunks: list[dict]) -> None:
        def _build() -> BM25Okapi | None:
            tokenized = [c["content"].lower().split() for c in chunks]
            return BM25Okapi(tokenized) if tokenized else None

        bm25 = await asyncio.to_thread(_build)
        self.chunks = chunks
        self.bm25 = bm25

    async def retrieve(
        self, query: str, top_k: int = 10, document_ids: list[str] | None = None
    ) -> list[dict]:
        # Snapshot refs so a concurrent rebuild can't swap them out mid-scoring.
        bm25, chunks = self.bm25, self.chunks
        if not bm25:
            return []

        allowed = set(document_ids) if document_ids else None

        def _score() -> list[dict]:
            scores = bm25.get_scores(query.lower().split())
            ranked = np.argsort(scores)[::-1]
            out: list[dict] = []
            for i in ranked:
                if scores[i] <= 0:
                    break  # rest are zero-relevance
                if allowed is not None and chunks[i]["document_id"] not in allowed:
                    continue
                out.append({**chunks[i], "score": float(scores[i])})
                if len(out) >= top_k:
                    break
            return out

        return await asyncio.to_thread(_score)


sparse_retriever = SparseRetriever()
