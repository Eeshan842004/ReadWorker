# Metrics

> **Status:** the evaluation harness is fully built and wired, but the numbers below are
> **placeholders** until you (a) add `GROQ_API_KEY` + `GOOGLE_API_KEY`, (b) fill in 30–50
> real golden QA pairs in `backend/eval_data/golden_qa.json`, and (c) run the eval. Do not
> quote these figures on a resume until they come from a real run — replace `TBD` with the
> output of `python -m app.evaluation.eval_runner`.

## How to generate real numbers

```bash
cd backend
# 1. Ensure keys are set in ../.env and the DB is running with documents ingested.
# 2. Fill eval_data/golden_qa.json with real question/ground_truth/contexts triples.
python -m app.evaluation.eval_runner        # writes eval_data/last_eval.json
```

The eval dashboard (`/eval`) reads `last_eval.json` and the `/eval/cost` summary.

## Targets

| Metric | Target | Source |
|--------|--------|--------|
| Context precision @5 | > 85% | ragas `context_precision` |
| Faithfulness | > 90% | ragas `faithfulness` |
| Answer relevance | > 85% | ragas `answer_relevancy` |
| Context recall | > 80% | ragas `context_recall` |
| Latency p95 | < 3s | `query_logs.latency_ms` |
| Cost per query | $0.00 | Groq free tier |

## Results (fill in after a real run)

| Metric | Single-shot | Multi-agent | Δ |
|--------|-------------|-------------|---|
| Faithfulness | TBD | TBD | TBD |
| Context precision | TBD | TBD | TBD |
| Answer relevancy | TBD | TBD | TBD |
| Context recall | TBD | TBD | TBD |
| Avg latency | TBD | TBD | TBD |

## Strategy comparisons to record

- Fixed-size (1000/200) vs parent-child (2000/500) chunking.
- Dense-only vs hybrid (dense + BM25 RRF) vs hybrid + rerank.
- With vs without Gemini `task_type` prefixes.
