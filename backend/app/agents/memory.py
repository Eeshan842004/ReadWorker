"""Rolling conversation memory: summarize older turns with the cheap 8B model so the
context stays bounded while preserving continuity."""

from app.agents.llm import chat
from app.config import settings

MAX_TURNS_BEFORE_SUMMARY = 5

_SYSTEM = """Summarize the following conversation between a user and a research assistant
in 2-3 sentences, preserving key facts, entities, and the user's goals. Reply with only
the summary."""


async def summarize_history(history: list[dict]) -> str:
    """history: list of {"role": "user"|"assistant", "content": str}."""
    if not history:
        return ""
    transcript = "\n".join(f"{turn['role']}: {turn['content']}" for turn in history)
    try:
        return (await chat(_SYSTEM, transcript, model=settings.GROQ_FAST_MODEL, temperature=0)).strip()
    except Exception:
        return ""


async def compress_if_needed(history: list[dict]) -> list[dict]:
    """Collapse everything but the last turn into a single summary system note."""
    if len(history) <= MAX_TURNS_BEFORE_SUMMARY:
        return history
    older, recent = history[:-1], history[-1:]
    summary = await summarize_history(older)
    compressed = [{"role": "system", "content": f"Summary of earlier conversation: {summary}"}]
    return compressed + recent
