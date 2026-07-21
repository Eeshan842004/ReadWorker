from app.agents.guardrails import check_input, redact_pii
from app.agents.llm import chat
from app.agents.state import AgentState, trace
from app.config import settings

_SYSTEM = """You are a query clarifier. Rewrite the user question for optimal document retrieval.
- Fix typos and ambiguity
- Expand abbreviations
- Make the intent explicit
Reply with ONLY the rewritten query, no preamble."""


async def query_clarifier(state: AgentState) -> dict:
    question = state["question"]

    allowed, reason = check_input(question)
    if not allowed:
        return {
            "blocked": True,
            "block_reason": reason,
            "generation": "This request was blocked by input guardrails.",
            "trace_log": [trace("query_clarifier", f"BLOCKED: {reason}", status="blocked")],
        }

    safe_question = redact_pii(question)
    try:
        rewritten = (await chat(_SYSTEM, safe_question, model=settings.GROQ_FAST_MODEL, temperature=0)).strip()
    except Exception as exc:
        rewritten = safe_question
        return {
            "rewritten_query": rewritten,
            "trace_log": [trace("query_clarifier", f"LLM error, using raw query: {exc}", status="warn")],
        }

    rewritten = rewritten or safe_question
    return {
        "rewritten_query": rewritten,
        "trace_log": [trace("query_clarifier", f"'{question}' → '{rewritten}'", status="ok")],
    }
