from app.evaluation.eval_dataset import is_placeholder
from app.evaluation.metrics import gate_passed, summarize
from app.observability.cost_tracker import estimate_cost


def test_summarize_averages_metrics():
    per_q = [
        {"faithfulness": 0.9, "answer_relevancy": 0.8},
        {"faithfulness": 0.7, "answer_relevancy": 0.6},
    ]
    summary = summarize(per_q)
    assert summary["faithfulness"] == 0.8
    assert summary["answer_relevancy"] == 0.7


def test_gate_passed():
    assert gate_passed({"faithfulness": 0.85}, 0.8)
    assert not gate_passed({"faithfulness": 0.75}, 0.8)
    assert not gate_passed({}, 0.8)


def test_is_placeholder():
    assert is_placeholder({"ground_truth": "REPLACE WITH THE CORRECT ANSWER"})
    assert is_placeholder({"ground_truth": ""})
    assert not is_placeholder({"ground_truth": "Paris is the capital of France."})


def test_estimate_cost_free_tier():
    # Free tier price constant is 0, so any token count costs $0.
    assert estimate_cost(1_000_000) == 0.0


def test_parent_child_chunker_levels():
    import asyncio

    from app.ingestion.chunker import ParentChildChunker

    text = "Sentence about topic A. " * 200
    chunker = ParentChildChunker(parent_size=800, parent_overlap=100, child_size=200, child_overlap=40)
    parents, children = asyncio.run(chunker.chunk_document(text, "doc-x"))
    assert parents and children
    # Every child points at a real parent.
    parent_ids = {p["id"] for p in parents}
    assert all(c["parent_chunk_id"] in parent_ids for c in children)
    # Children carry parent content for small-to-big expansion.
    assert all(c["metadata"].get("parent_content") for c in children)
