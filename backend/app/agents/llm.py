"""Async Groq chat helper shared by all agent nodes.

Handles model routing, token accounting, and free-tier resilience: transient rate limits
are retried with backoff, and a model whose daily token budget is exhausted automatically
falls back to the smaller model rather than failing the request.
"""

import asyncio

from openai import RateLimitError

from app.config import settings
from app.groq_client import get_groq_client

# Process-wide token counter for the current request. Reset per pipeline run.
_token_usage: dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}

# Records model fallbacks so the trace/response can surface them.
_fallback_events: list[str] = []

MAX_RETRIES = 3
BACKOFF_BASE_SECONDS = 1.5


def reset_token_usage() -> None:
    _token_usage.update(prompt=0, completion=0, total=0)
    _fallback_events.clear()


def get_token_usage() -> dict[str, int]:
    return dict(_token_usage)


def get_fallback_events() -> list[str]:
    return list(_fallback_events)


def route_model(query: str) -> str:
    """Short, simple queries → fast 8B model; anything else → 70B for reasoning."""
    if len(query.split()) < 15 and "?" not in query:
        return settings.GROQ_FAST_MODEL
    return settings.GROQ_SYNTHESIS_MODEL


def _is_daily_cap(exc: Exception) -> bool:
    """A per-day cap won't clear on a short retry — fall back to another model instead."""
    msg = str(exc).lower()
    return "tokens per day" in msg or "tpd" in msg or "requests per day" in msg or "rpd" in msg


def _sync_call(model: str, system: str, user: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = get_groq_client().chat.completions.create(**kwargs)
    if response.usage:
        _token_usage["prompt"] += response.usage.prompt_tokens
        _token_usage["completion"] += response.usage.completion_tokens
        _token_usage["total"] += response.usage.total_tokens
    return response.choices[0].message.content or ""


async def chat(
    system: str,
    user: str,
    model: str | None = None,
    temperature: float = 0.1,
    max_tokens: int = 1024,
    json_mode: bool = False,
) -> str:
    """Call Groq, surviving free-tier rate limits.

    Strategy per model: retry transient (per-minute) limits with exponential backoff; on a
    per-day cap, stop retrying that model immediately and fall back to the smaller one.
    """
    primary = model or settings.GROQ_SYNTHESIS_MODEL
    candidates = [primary]
    if primary != settings.GROQ_FAST_MODEL:
        candidates.append(settings.GROQ_FAST_MODEL)

    last_exc: Exception | None = None

    for index, candidate in enumerate(candidates):
        if index > 0:
            _fallback_events.append(f"{primary} exhausted → fell back to {candidate}")

        for attempt in range(MAX_RETRIES):
            try:
                return await _run(candidate, system, user, temperature, max_tokens, json_mode)
            except RateLimitError as exc:
                last_exc = exc
                if _is_daily_cap(exc):
                    break  # a short wait won't help; try the next model
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(BACKOFF_BASE_SECONDS * (2**attempt))

    raise last_exc if last_exc else RuntimeError("Groq chat failed with no exception recorded")


async def _run(model: str, system: str, user: str, temperature: float, max_tokens: int, json_mode: bool) -> str:
    return await asyncio.to_thread(_sync_call, model, system, user, temperature, max_tokens, json_mode)
