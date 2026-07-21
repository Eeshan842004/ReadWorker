import asyncio
from functools import cached_property

from langchain_google_genai import GoogleGenerativeAIEmbeddings

from app.config import settings

BATCH_SIZE = 10
BATCH_DELAY_SECONDS = 0.5


class EmbeddingService:
    """Builds Gemini clients lazily so the app can boot without GOOGLE_API_KEY set."""

    @cached_property
    def doc_embedder(self) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.GOOGLE_API_KEY,
            task_type="RETRIEVAL_DOCUMENT",
        )

    @cached_property
    def query_embedder(self) -> GoogleGenerativeAIEmbeddings:
        return GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            google_api_key=settings.GOOGLE_API_KEY,
            task_type="RETRIEVAL_QUERY",
        )

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            embeddings = await asyncio.to_thread(self.doc_embedder.embed_documents, batch)
            all_embeddings.extend(embeddings)
            if i + BATCH_SIZE < len(texts):
                await asyncio.sleep(BATCH_DELAY_SECONDS)
        return all_embeddings

    async def embed_query(self, query: str) -> list[float]:
        return await asyncio.to_thread(self.query_embedder.embed_query, query)


embedding_service = EmbeddingService()
