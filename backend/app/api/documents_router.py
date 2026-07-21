from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select

from app.database.connection import get_session
from app.database.models import Chunk, Document, EvalQuestion
from app.ingestion.router import rebuild_sparse_index

router = APIRouter()


@router.get("/documents")
async def list_documents():
    async with get_session() as session:
        result = await session.execute(select(Document))
        docs = result.scalars().all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "uploaded_at": d.uploaded_at,
                "total_chunks": d.total_chunks,
            }
            for d in docs
        ]


@router.delete("/documents")
async def clear_all_documents():
    """Wipe every document, its chunks, and its auto-generated test questions."""
    async with get_session() as session:
        await session.execute(delete(Chunk))
        await session.execute(delete(EvalQuestion))
        result = await session.execute(delete(Document))
        await session.commit()
        removed = result.rowcount or 0
    await rebuild_sparse_index()  # now empty
    return {"cleared": removed}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    async with get_session() as session:
        doc = await session.get(Document, document_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        await session.execute(delete(Chunk).where(Chunk.document_id == document_id))
        await session.execute(delete(EvalQuestion).where(EvalQuestion.document_id == document_id))
        await session.delete(doc)
        await session.commit()
    return {"deleted": document_id}
