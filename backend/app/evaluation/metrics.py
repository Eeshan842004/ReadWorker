"""Helpers for summarizing evaluation results independent of ragas internals."""

import math
from statistics import mean

RAGAS_METRIC_NAMES = [
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
]


def _finite(value) -> bool:
    # ragas emits NaN for a sample it couldn't score (e.g. exhausted rate-limit retries).
    return isinstance(value, (int, float)) and math.isfinite(value)


def summarize(per_question: list[dict]) -> dict[str, float]:
    """Average each metric across all questions. Missing/NaN values are skipped."""
    summary: dict[str, float] = {}
    for metric in RAGAS_METRIC_NAMES:
        values = [row[metric] for row in per_question if _finite(row.get(metric))]
        if values:
            summary[metric] = round(mean(values), 4)
    return summary


def gate_passed(summary: dict[str, float], threshold: float) -> bool:
    """Faithfulness must clear the threshold for CI to pass."""
    return summary.get("faithfulness", 0.0) >= threshold
