"""Auto-generate an evaluation golden set from a freshly-ingested document.

One cheap 8B LLM call produces N question / ground-truth pairs grounded in the document;
each pair is then streamed to the UI with a short delay so the user watches the test set
being written live. Failure is non-fatal — a document still ingests if generation fails.
"""

import asyncio
import json

from app.agents.llm import chat
from app.config import settings

DEFAULT_N = 5
MAX_SOURCE_CHARS = 6000       # keep the prompt cheap and within context
REVEAL_DELAY_SECONDS = 0.45   # pacing for the live "writing" animation

_SYSTEM = """You build evaluation test sets for a document Q&A system.
From the document, write {n} diverse question/answer pairs.

Rules:
- Each question must be answerable ONLY from the document.
- Each answer must be directly supported by the text (quote or close paraphrase), 1-3 sentences.
- Cover DIFFERENT parts of the document; do not repeat.
Reply as JSON: {{"pairs": [{{"question": "...", "answer": "..."}}]}}"""


def _parse_pairs(raw: str) -> list[dict]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    pairs = data.get("pairs") if isinstance(data, dict) else data
    if not isinstance(pairs, list):
        return []
    clean = []
    for p in pairs:
        if isinstance(p, dict) and p.get("question") and p.get("answer"):
            clean.append({"question": str(p["question"]).strip(), "answer": str(p["answer"]).strip()})
    return clean


async def generate_and_stream(text: str, n: int = DEFAULT_N, ws_callback=None) -> list[dict]:
    """Return a list of {question, ground_truth, contexts}; stream each over ws_callback.

    Never raises — returns [] on any failure so ingestion is unaffected.
    """
    source = text.strip()
    if len(source) < 200:  # too little content to build a meaningful test set
        return []

    sample = source[:MAX_SOURCE_CHARS]

    if ws_callback:
        await ws_callback({"type": "qa_generation_start", "expected": n})

    try:
        raw = await chat(
            system=_SYSTEM.format(n=n),
            user=sample,
            model=settings.GROQ_FAST_MODEL,
            temperature=0.3,
            max_tokens=1200,
            json_mode=True,
        )
        pairs = _parse_pairs(raw)
    except Exception as exc:
        if ws_callback:
            await ws_callback({"type": "qa_generation_error", "message": str(exc)[:200]})
        return []

    result: list[dict] = []
    for i, pair in enumerate(pairs):
        item = {
            "question": pair["question"],
            "ground_truth": pair["answer"],
            "contexts": [sample[:1200]],
        }
        result.append(item)
        if ws_callback:
            await ws_callback(
                {
                    "type": "qa_generated",
                    "index": i,
                    "total": len(pairs),
                    "question": pair["question"],
                    "answer": pair["answer"],
                }
            )
            await asyncio.sleep(REVEAL_DELAY_SECONDS)

    if ws_callback:
        await ws_callback({"type": "qa_complete", "total": len(result)})
    return result
