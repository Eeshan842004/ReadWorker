import time
import traceback

from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import func, select

from app.database.connection import get_session
from app.database.models import Document, EvalQuestion
from app.evaluation.eval_runner import load_last_results, run_evaluation
from app.observability.cost_tracker import get_cost_summary
from app.observability.logging import get_logger

router = APIRouter(prefix="/eval", tags=["evaluation"])
log = get_logger("eval")

_running = {"in_progress": False}
_last_error: dict | None = None


async def _run_and_flag(document_id: str | None):
    global _last_error
    _running["in_progress"] = True
    _last_error = None
    try:
        await run_evaluation(document_id=document_id)
    except Exception as exc:
        # A background task's exception is otherwise swallowed silently — the UI would
        # just flip back to "no results" with zero explanation. Surface it instead.
        log.error("eval_run_failed", document_id=document_id, error=str(exc))
        _last_error = {
            "message": f"{type(exc).__name__}: {exc}",
            "trace": traceback.format_exc()[-2000:],
            "document_id": document_id,
            "at": time.time(),
        }
    finally:
        _running["in_progress"] = False


@router.post("/run")
async def trigger_eval(background_tasks: BackgroundTasks, document_id: str | None = None):
    """Kick off a ragas evaluation in the background (needs GROQ + GOOGLE keys).

    Pass `document_id` to grade only that document's auto-generated test set.
    """
    if _running["in_progress"]:
        return {"status": "already_running"}
    background_tasks.add_task(_run_and_flag, document_id)
    return {"status": "started"}


@router.get("/results")
async def eval_results():
    results = load_last_results()
    return results or {"status": "no_results", "summary": {}, "per_question": []}


@router.get("/status")
async def eval_status():
    return {"in_progress": _running["in_progress"], "last_error": _last_error}


@router.get("/questions")
async def eval_questions():
    """Auto-generated test sets grouped by document, with a few sample questions each."""
    async with get_session() as session:
        counts = (
            await session.execute(
                select(
                    EvalQuestion.document_id,
                    Document.filename,
                    func.count(EvalQuestion.id),
                )
                .join(Document, Document.id == EvalQuestion.document_id)
                .group_by(EvalQuestion.document_id, Document.filename)
            )
        ).all()

        sets = []
        for doc_id, filename, count in counts:
            samples = (
                await session.execute(
                    select(EvalQuestion.question)
                    .where(EvalQuestion.document_id == doc_id)
                    .limit(3)
                )
            ).scalars().all()
            sets.append(
                {"document_id": doc_id, "filename": filename, "count": int(count), "samples": samples}
            )

        total = sum(s["count"] for s in sets)
    return {"total_questions": total, "sets": sets}


@router.get("/cost")
async def cost_summary():
    return await get_cost_summary()
