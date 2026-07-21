"""ragas evaluation runner.

Runs the RAG pipeline over the golden QA set and scores it with ragas
(faithfulness, answer relevancy, context precision/recall) using Groq as the judge LLM
and Gemini as the judge embeddings — zero paid API cost.

Usable both as a library (`run_evaluation`) and as a CLI gate for CI:

    python -m app.evaluation.eval_runner

Exits non-zero if faithfulness < settings.FAITHFULNESS_GATE.
"""

import asyncio
import json
import math
import sys
from pathlib import Path

from app.config import settings
from app.evaluation.eval_dataset import usable_golden_qa
from app.evaluation.metrics import RAGAS_METRIC_NAMES, gate_passed, summarize

RESULTS_PATH = Path(__file__).resolve().parents[2] / "eval_data" / "last_eval.json"


def _sanitize(obj):
    """Recursively turn non-finite floats (NaN/Inf) into None so the payload is valid JSON.

    ragas returns NaN for a sample it couldn't score (e.g. exhausted rate-limit retries);
    NaN is not JSON-serializable and would otherwise crash the API response.
    """
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(v) for v in obj]
    return obj


def _judge_llm():
    from langchain_openai import ChatOpenAI

    # Use the fast 8B model as the ragas judge: it has a much larger daily token budget
    # than the 70B and far fewer rate-limit stalls, so eval runs actually complete on the
    # free tier. Slightly weaker judgments are an acceptable trade for reliability.
    return ChatOpenAI(
        model=settings.GROQ_FAST_MODEL,
        api_key=settings.GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
        temperature=0,
        max_retries=5,
    )


async def _build_samples(golden: list[dict], document_ids: list[str] | None = None) -> list[dict]:
    """Run the live pipeline to produce (question, answer, contexts, ground_truth).

    When scoped to a document, the pipeline only retrieves from that document — so the
    answer under test is grounded in the same source as the reference.
    """
    from app.agents.graph import run_pipeline

    samples = []
    for item in golden:
        result = await run_pipeline(item["question"], document_ids=document_ids)
        contexts = [d["content"] for d in result.get("reranked_documents", [])]
        samples.append(
            {
                "user_input": item["question"],
                "response": result.get("generation", ""),
                "retrieved_contexts": contexts or item.get("contexts", []),
                "reference": item.get("ground_truth", ""),
            }
        )
    return samples


def _run_ragas(samples: list[dict]) -> list[dict]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    from app.ingestion.embedder import embedding_service

    from ragas.run_config import RunConfig

    # answer_relevancy generates several probe questions per answer. By default it asks the
    # LLM for them in one call via `n=strictness`, but Groq only supports n=1 (400 otherwise).
    # strictness=1 makes it a single valid completion.
    answer_relevancy.strictness = 1

    dataset = Dataset.from_list(samples)
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=LangchainLLMWrapper(_judge_llm()),
        embeddings=LangchainEmbeddingsWrapper(embedding_service.doc_embedder),
        # Throttle: Groq free tier is 30 RPM. Few concurrent workers + retries keeps the
        # judge under the limit instead of blasting parallel requests into 429s.
        run_config=RunConfig(max_workers=2, max_retries=5, timeout=180),
    )
    df = result.to_pandas()
    return df.to_dict(orient="records")


async def load_db_questions(document_id: str | None = None) -> list[dict]:
    """Auto-generated test sets (created at upload) take priority over the static json.

    With `document_id`, only that document's questions are returned — so a document is
    graded strictly on its own test set, never on other documents' questions.
    """
    from sqlalchemy import select

    from app.database.connection import get_session
    from app.database.models import EvalQuestion

    stmt = select(EvalQuestion.question, EvalQuestion.ground_truth, EvalQuestion.contexts)
    if document_id:
        stmt = stmt.where(EvalQuestion.document_id == document_id)

    async with get_session() as session:
        rows = (await session.execute(stmt)).all()
    return [{"question": q, "ground_truth": gt, "contexts": ctx or []} for q, gt, ctx in rows]


async def _document_name(document_id: str) -> str | None:
    from app.database.connection import get_session
    from app.database.models import Document

    async with get_session() as session:
        doc = await session.get(Document, document_id)
        return doc.filename if doc else None


async def run_evaluation(golden: list[dict] | None = None, document_id: str | None = None) -> dict:
    if golden is None:
        golden = await load_db_questions(document_id) or (usable_golden_qa() if not document_id else [])
    if not golden:
        return {
            "status": "skipped",
            "reason": "No test questions yet. Upload a document — a test set is generated automatically.",
            "summary": {},
            "per_question": [],
        }

    scoped_document_ids = [document_id] if document_id else None

    samples = await _build_samples(golden, document_ids=scoped_document_ids)
    # ragas.evaluate() manages its own event loop internally, which conflicts with the
    # one already running this coroutine — uvloop (Render's Linux default) refuses that
    # outright ("Cannot execute nested async code"), while the plain asyncio loop
    # (Windows dev machines) happens to tolerate it. Running it in a worker thread avoids
    # the conflict on every platform, not just the one where it happened to work by luck.
    per_question = _sanitize(await asyncio.to_thread(_run_ragas, samples))
    summary = summarize(per_question)

    report = {
        "status": "completed",
        "document_id": document_id,
        "document_name": await _document_name(document_id) if document_id else None,
        "num_questions": len(golden),
        "summary": summary,
        "per_question": per_question,
        "gate": {
            "metric": "faithfulness",
            "threshold": settings.FAITHFULNESS_GATE,
            "passed": gate_passed(summary, settings.FAITHFULNESS_GATE),
        },
    }
    # allow_nan=False guarantees the persisted file is strict, valid JSON.
    RESULTS_PATH.write_text(
        json.dumps(report, indent=2, default=str, allow_nan=False), encoding="utf-8"
    )
    return report


def load_last_results() -> dict | None:
    if RESULTS_PATH.exists():
        # Older files may contain NaN literals; sanitize so the API returns valid JSON.
        return _sanitize(json.loads(RESULTS_PATH.read_text(encoding="utf-8")))
    return None


def _main() -> int:
    report = asyncio.run(run_evaluation())
    print(json.dumps(report.get("summary", {}), indent=2))

    if report["status"] == "skipped":
        print(f"[eval] SKIPPED: {report['reason']}")
        return 0  # don't fail CI just because the dataset is a template

    passed = report["gate"]["passed"]
    faith = report["summary"].get("faithfulness", 0.0)
    print(
        f"[eval] faithfulness={faith:.3f} threshold={settings.FAITHFULNESS_GATE} "
        f"→ {'PASS' if passed else 'FAIL'}"
    )
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(_main())


# Keep metric names importable for the API layer.
__all__ = ["run_evaluation", "load_last_results", "RAGAS_METRIC_NAMES"]
