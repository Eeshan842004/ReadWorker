"""Per-request token + cost accounting, persisted to the query_logs table."""

from sqlalchemy import func, select

from app.config import settings
from app.database.connection import get_session
from app.database.models import QueryLog


def estimate_cost(total_tokens: int) -> float:
    """Groq free tier = $0. Kept as a formula so a paid tier can be priced later."""
    return round(total_tokens / 1_000_000 * settings.COST_PER_1M_TOKENS_USD, 6)


async def log_query(
    *,
    question: str,
    answer: str,
    model: str,
    token_usage: dict,
    latency_ms: float,
    trace_id: str | None = None,
    user_id: str | None = None,
    faithfulness_score: float | None = None,
) -> None:
    total = token_usage.get("total", 0)
    async with get_session() as session:
        session.add(
            QueryLog(
                user_id=user_id,
                trace_id=trace_id,
                question=question,
                answer=answer,
                model=model,
                prompt_tokens=token_usage.get("prompt", 0),
                completion_tokens=token_usage.get("completion", 0),
                total_tokens=total,
                cost_usd=estimate_cost(total),
                latency_ms=latency_ms,
                faithfulness_score=faithfulness_score,
            )
        )
        await session.commit()


async def get_cost_summary() -> dict:
    async with get_session() as session:
        result = await session.execute(
            select(
                func.count(QueryLog.id),
                func.coalesce(func.sum(QueryLog.total_tokens), 0),
                func.coalesce(func.sum(QueryLog.cost_usd), 0.0),
                func.coalesce(func.avg(QueryLog.latency_ms), 0.0),
                func.coalesce(func.avg(QueryLog.faithfulness_score), 0.0),
            )
        )
        count, tokens, cost, avg_latency, avg_faith = result.one()
        return {
            "total_queries": int(count),
            "total_tokens": int(tokens),
            "total_cost_usd": round(float(cost), 6),
            "avg_latency_ms": round(float(avg_latency), 1),
            "avg_faithfulness": round(float(avg_faith), 3),
        }
