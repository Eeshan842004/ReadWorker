from fastapi import APIRouter, BackgroundTasks
from sqlalchemy import func, select

from app.database.connection import get_session
from app.database.models import Document, EvalQuestion
from app.evaluation.eval_runner import load_last_results, run_evaluation
from app.observability.cost_tracker import get_cost_summary

router = APIRouter(prefix="/eval", tags=["evaluation"])

_running = {"in_progress": False}


async def _run_and_flag(document_id: str | None):
    _running["in_progress"] = True
    try:
        await run_evaluation(document_id=document_id)
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
    return {"in_progress": _running["in_progress"]}


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
