import asyncio

from app.retrieval.dense_retriever import DenseRetriever, dense_retriever
from app.retrieval.sparse_retriever import SparseRetriever, sparse_retriever


class HybridRetriever:
    def __init__(self, dense: DenseRetriever, sparse: SparseRetriever):
        self.dense = dense
        self.sparse = sparse

    async def retrieve(
        self,
        query: str,
        query_embedding: list[float],
        top_k: int = 10,
        rrf_k: int = 60,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        # Dense hits the DB, sparse scores in a worker thread — overlap them.
        dense_results, sparse_results = await asyncio.gather(
            self.dense.retrieve(query_embedding, top_k=top_k * 2, document_ids=document_ids),
            self.sparse.retrieve(query, top_k=top_k * 2, document_ids=document_ids),
        )

        doc_map = {d["id"]: d for d in dense_results + sparse_results}

        rrf_scores: dict[str, float] = {}
        for rank, doc in enumerate(dense_results):
            rrf_scores[doc["id"]] = rrf_scores.get(doc["id"], 0) + 1 / (rrf_k + rank + 1)
        for rank, doc in enumerate(sparse_results):
            rrf_scores[doc["id"]] = rrf_scores.get(doc["id"], 0) + 1 / (rrf_k + rank + 1)

        sorted_ids = sorted(rrf_scores, key=rrf_scores.get, reverse=True)[:top_k]
        return [{**doc_map[did], "rrf_score": rrf_scores[did]} for did in sorted_ids if did in doc_map]


hybrid_retriever = HybridRetriever(dense_retriever, sparse_retriever)
