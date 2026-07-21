import json

from app.agents.llm import chat
from app.agents.state import AgentState, trace
from app.config import settings

_SYSTEM = """Decompose the question into 1-3 sub-questions that can each be answered
independently via document retrieval. Reply as a JSON object of the form
{"questions": ["...", "..."]}. If the question is already simple, return it unchanged
as the single element."""


def _parse_sub_questions(raw: str, fallback: str) -> list[str]:
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            qs = data.get("questions") or data.get("sub_questions") or []
        elif isinstance(data, list):
            qs = data
        else:
            qs = []
        qs = [q for q in qs if isinstance(q, str) and q.strip()]
        return qs or [fallback]
    except (json.JSONDecodeError, TypeError):
        return [fallback]


async def planner(state: AgentState) -> dict:
    query = state["rewritten_query"]
    try:
        raw = await chat(_SYSTEM, query, model=settings.GROQ_SYNTHESIS_MODEL, temperature=0, json_mode=True)
        sub_qs = _parse_sub_questions(raw, query)
    except Exception as exc:
        return {
            "sub_questions": [query],
            "trace_log": [trace("planner", f"LLM error, no decomposition: {exc}", status="warn")],
        }

    return {
        "sub_questions": sub_qs,
        "trace_log": [trace("planner", f"decomposed into {len(sub_qs)} sub-question(s)", sub_questions=sub_qs, status="ok")],
    }
