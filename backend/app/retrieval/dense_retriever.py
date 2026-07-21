from sqlalchemy import select

from app.database.connection import get_session
from app.database.models import Chunk


class DenseRetriever:
    """Cosine-similarity search over pgvector.

    Uses pgvector's SQLAlchemy integration (`cosine_distance`) rather than raw SQL:
    a raw `text()` query cannot express the `:query_vec::vector` cast, because
    SQLAlchemy's bind-parameter parser collides with Postgres' `::` cast operator.
    """

    async def retrieve(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        document_ids: list[str] | None = None,
    ) -> list[dict]:
        distance = Chunk.embedding.cosine_distance(query_embedding)
        stmt = (
            select(
                Chunk.id,
                Chunk.content,
                Chunk.metadata_,
                Chunk.document_id,
                (1 - distance).label("similarity"),
            )
            .order_by(distance)
            .limit(top_k)
        )
        if document_ids:
            stmt = stmt.where(Chunk.document_id.in_(document_ids))

        async with get_session() as session:
            result = await session.execute(stmt)
            return [
                {
                    "id": row.id,
                    "content": row.content,
                    "metadata": row.metadata_,
                    "document_id": row.document_id,
                    "score": float(row.similarity),
                }
                for row in result.all()
            ]


dense_retriever = DenseRetriever()
