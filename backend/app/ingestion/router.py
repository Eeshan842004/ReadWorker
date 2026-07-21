import uuid

from fastapi import APIRouter, Query, UploadFile
from sqlalchemy import delete, select

from app.api.ws_router import connection_manager
from app.database.connection import get_session, with_db_retry
from app.database.models import Chunk, Document, EvalQuestion
from app.evaluation.question_generator import generate_and_stream
from app.ingestion.chunker import ParentChildChunker
from app.ingestion.embedder import embedding_service
from app.ingestion.processor import extract_text
from app.observability.logging import get_logger
from app.retrieval.sparse_retriever import sparse_retriever

router = APIRouter()
chunker = ParentChildChunker()
log = get_logger("ingest")


@router.post("/ingest/upload")
async def upload_document(file: UploadFile, document_id: str | None = Query(default=None)):
    doc_id = document_id or str(uuid.uuid4())
    raw_bytes = await file.read()
    text = extract_text(file.filename, file.content_type, raw_bytes)

    async def ws_callback(event: dict) -> None:
        await connection_manager.broadcast(doc_id, event)

    parents, children = await chunker.chunk_document(text, doc_id, ws_callback=ws_callback)

    # Only children get embedded + indexed (small-to-big retrieval).
    embeddings = await embedding_service.embed_documents([c["content"] for c in children])

    async def _persist() -> None:
        async with get_session() as session:
            # Auto-replace: drop any existing document with the same filename (and its
            # chunks + test questions) so re-uploading a file refreshes it instead of
            # piling up duplicates.
            dupes = (
                await session.execute(select(Document.id).where(Document.filename == file.filename))
            ).scalars().all()
            if dupes:
                await session.execute(delete(Chunk).where(Chunk.document_id.in_(dupes)))
                await session.execute(delete(EvalQuestion).where(EvalQuestion.document_id.in_(dupes)))
                await session.execute(delete(Document).where(Document.id.in_(dupes)))

            session.add(
                Document(
                    id=doc_id,
                    filename=file.filename,
                    content_type=file.content_type,
                    total_chunks=len(children),
                    metadata_={"parent_chunks": len(parents), "child_chunks": len(children)},
                )
            )
            for chunk, embedding in zip(children, embeddings):
                session.add(
                    Chunk(
                        id=chunk["id"],
                        document_id=doc_id,
                        content=chunk["content"],
                        chunk_index=chunk["chunk_index"],
                        embedding=embedding,
                        metadata_=chunk["metadata"],
                        parent_chunk_id=chunk.get("parent_chunk_id"),
                    )
                )
            await session.commit()

    # Retry once on a serverless-DB disconnect (Neon cold start / idle suspend).
    await with_db_retry(_persist)

    await connection_manager.broadcast(
        doc_id,
        {"type": "ingest_complete", "total_chunks": len(children), "parent_chunks": len(parents)},
    )
    await rebuild_sparse_index()

    # Auto-build an evaluation test set from this document, streamed live to the UI.
    eval_count = 0
    try:
        pairs = await generate_and_stream(text, ws_callback=ws_callback)
        if pairs:
            async def _persist_eval() -> None:
                async with get_session() as session:
                    for p in pairs:
                        session.add(
                            EvalQuestion(
                                document_id=doc_id,
                                question=p["question"],
                                ground_truth=p["ground_truth"],
                                contexts=p["contexts"],
                            )
                        )
                    await session.commit()

            await with_db_retry(_persist_eval)
            eval_count = len(pairs)
    except Exception as exc:  # never fail the upload over the test set
        log.warning("qa_generation_failed", error=str(exc))

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "total_chunks": len(children),
        "parent_chunks": len(parents),
        "eval_questions": eval_count,
    }


async def rebuild_sparse_index() -> None:
    """Rebuild the in-memory BM25 index from all persisted child chunks.

    Selects only the columns BM25 needs — pulling full ORM entities would drag every
    3072-dim embedding vector across the wire on each upload and at startup.
    """

    async def _fetch() -> list[dict]:
        async with get_session() as session:
            result = await session.execute(
                select(Chunk.id, Chunk.content, Chunk.document_id, Chunk.metadata_)
            )
            return [
                {"id": r.id, "content": r.content, "document_id": r.document_id, "metadata": r.metadata_}
                for r in result.all()
            ]

    all_chunks = await with_db_retry(_fetch)
    await sparse_retriever.build_index(all_chunks)
