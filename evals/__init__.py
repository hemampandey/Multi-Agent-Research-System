"""Evaluations: measure report quality on a fixed dataset so changes can be compared.

- dataset.jsonl  the cases: real topics, plus topics the guardrails must block
- metrics.py     cheap, deterministic, code-based scores (citations, structure, ...)
- judge.py       LLM-as-judge for what code can't check (groundedness, relevance)
- run_evals.py   runs everything, applies pass thresholds, saves and diffs results
"""
