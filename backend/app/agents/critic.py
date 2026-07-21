import json

from app.agents.llm import chat
from app.agents.state import AgentState, trace
from app.config import settings

_SYSTEM = """You are a faithfulness auditor. Given an answer and its source documents,
score how well every claim is supported by the sources, from 0.0 to 1.0.
- 1.0 = every claim is fully supported
- 0.0 = entirely fabricated / unsupported
Reply with ONLY a JSON object: {"score": <float>, "issues": "<brief description or 'none'>"}"""

MAX_RETRIES = 2
FAITHFULNESS_RETRY_THRESHOLD = 0.7


async def critic(state: AgentState) -> dict:
    context = "\n".join(d["content"][:300] for d in state["reranked_documents"])
    user = f"Answer: {state['generation'][:800]}\n\nSources: {context}"

    score, issues = 0.5, "parsing error"
    try:
        raw = await chat(_SYSTEM, user, model=settings.GROQ_FAST_MODEL, temperature=0, json_mode=True)
        result = json.loads(raw)
        score = float(result.get("score", 0.0))
        issues = result.get("issues", "none")
    except Exception as exc:
        issues = f"critic error: {exc}"

    retry_count = state.get("retry_count", 0)
    needs_retry = score < FAITHFULNESS_RETRY_THRESHOLD and retry_count < MAX_RETRIES

    return {
        "faithfulness_score": score,
        "needs_re_retrieval": needs_retry,
        "retry_count": retry_count + (1 if needs_retry else 0),
        "trace_log": [
            trace(
                "critic",
                f"faithfulness={score:.2f}, issues='{issues}', retry={needs_retry}",
                score=score,
                status="warn" if needs_retry else "ok",
            )
        ],
    }
