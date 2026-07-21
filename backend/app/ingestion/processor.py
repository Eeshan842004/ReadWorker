import io

from docx import Document as DocxDocument
from pypdf import PdfReader


def extract_text(filename: str, content_type: str | None, raw_bytes: bytes) -> str:
    lower_name = filename.lower()

    if lower_name.endswith(".pdf") or content_type == "application/pdf":
        reader = PdfReader(io.BytesIO(raw_bytes))
        return "\n\n".join(page.extract_text() or "" for page in reader.pages)

    if lower_name.endswith(".docx"):
        doc = DocxDocument(io.BytesIO(raw_bytes))
        return "\n\n".join(p.text for p in doc.paragraphs)

    return raw_bytes.decode("utf-8", errors="ignore")
