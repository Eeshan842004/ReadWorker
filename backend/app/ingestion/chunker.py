import uuid
from typing import Awaitable, Callable, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.config import settings

WsCallback = Optional[Callable[[dict], Awaitable[None]]]

_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


class DocumentChunker:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=_SEPARATORS,
        )

    async def chunk_document(self, text: str, doc_id: str, ws_callback: WsCallback = None) -> list[dict]:
        chunks = self.splitter.split_text(text)
        result = []
        for i, chunk_text in enumerate(chunks):
            chunk = {
                "id": str(uuid.uuid4()),
                "document_id": doc_id,
                "content": chunk_text,
                "chunk_index": i,
                "metadata": {
                    "char_count": len(chunk_text),
                    "word_count": len(chunk_text.split()),
                },
            }
            result.append(chunk)
            if ws_callback:
                await ws_callback(
                    {
                        "type": "chunk_created",
                        "chunk_index": i,
                        "total_expected": len(chunks),
                        "preview": chunk_text[:100] + ("..." if len(chunk_text) > 100 else ""),
                        "char_count": len(chunk_text),
                    }
                )
        return result


class ParentChildChunker:
    """Parent-child (small-to-big) chunking.

    Splits the document into large *parent* chunks, then splits each parent into
    smaller *child* chunks. Retrieval runs over children (precise matching), but the
    parent text is returned to the synthesizer for richer context. Each child carries
    ``parent_chunk_id`` and ``parent_content`` in its metadata.
    """

    def __init__(
        self,
        parent_size: int | None = None,
        parent_overlap: int | None = None,
        child_size: int | None = None,
        child_overlap: int | None = None,
    ):
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_size or settings.PARENT_CHUNK_SIZE,
            chunk_overlap=parent_overlap or settings.PARENT_CHUNK_OVERLAP,
            separators=_SEPARATORS,
        )
        self.child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=child_size or settings.CHILD_CHUNK_SIZE,
            chunk_overlap=child_overlap or settings.CHILD_CHUNK_OVERLAP,
            separators=_SEPARATORS,
        )

    async def chunk_document(
        self, text: str, doc_id: str, ws_callback: WsCallback = None
    ) -> tuple[list[dict], list[dict]]:
        """Return (parents, children). Children are what get embedded and indexed."""
        parents: list[dict] = []
        children: list[dict] = []
        child_index = 0

        parent_texts = self.parent_splitter.split_text(text)
        for p_idx, parent_text in enumerate(parent_texts):
            parent_id = str(uuid.uuid4())
            parents.append(
                {
                    "id": parent_id,
                    "document_id": doc_id,
                    "content": parent_text,
                    "chunk_index": p_idx,
                    "metadata": {"char_count": len(parent_text), "level": "parent"},
                }
            )

            for child_text in self.child_splitter.split_text(parent_text):
                child = {
                    "id": str(uuid.uuid4()),
                    "document_id": doc_id,
                    "content": child_text,
                    "chunk_index": child_index,
                    "parent_chunk_id": parent_id,
                    "metadata": {
                        "char_count": len(child_text),
                        "word_count": len(child_text.split()),
                        "level": "child",
                        "parent_chunk_id": parent_id,
                        "parent_content": parent_text,
                    },
                }
                children.append(child)
                if ws_callback:
                    await ws_callback(
                        {
                            "type": "chunk_created",
                            "chunk_index": child_index,
                            "parent_index": p_idx,
                            "total_expected": None,
                            "preview": child_text[:100] + ("..." if len(child_text) > 100 else ""),
                            "char_count": len(child_text),
                        }
                    )
                child_index += 1

        if ws_callback:
            await ws_callback(
                {
                    "type": "chunking_summary",
                    "parents": len(parents),
                    "children": len(children),
                }
            )
        return parents, children
