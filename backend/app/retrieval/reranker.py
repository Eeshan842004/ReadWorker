import asyncio

from app.config import settings
from app.groq_client import get_groq_client

_SYSTEM_PROMPT = "Rate how relevant the passage is to the query on a 0-10 scale. Reply with ONLY the number."


class LLMReranker:
    """Use Groq's fast 8B model as a pointwise reranker.

    Scores each candidate chunk 0-10 for relevance to the query, then returns the
    top_k by score. Bounded to `max_candidates` to stay within free-tier rate limits.
    """

    def __init__(self, max_candidates: int = 15):
        self.max_candidates = max_candidates

    async def _score(self, query: str, content: str) -> float:
        def _call() -> str:
            response = get_groq_client().chat.completions.create(
                model=settings.GROQ_FAST_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": f"Query: {query}\n\nPassage: {content[:500]}"},
                ],
                temperature=0,
                max_tokens=5,
            )
            return (response.choices[0].message.content or "").strip()

        try:
            raw = await asyncio.to_thread(_call)
            # Guard against models that reply "8/10" or "Score: 7".
            digits = "".join(ch for ch in raw if ch.isdigit() or ch == ".")
            return min(float(digits), 10.0) if digits else 0.0
        except Exception:
            return 0.0

    async def rerank(self, query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
        candidates = chunks[: self.max_candidates]
        scores = await asyncio.gather(*(self._score(query, c["content"]) for c in candidates))
        scored = [{**chunk, "rerank_score": score} for chunk, score in zip(candidates, scores)]
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]


reranker = LLMReranker()
