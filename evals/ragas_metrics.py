"""Ragas: an off-the-shelf library of RAG evaluation metrics.

Our own metrics (metrics.py, judge.py) are written for this app. Ragas adds
two standard metrics with a more rigorous method:

- Faithfulness: splits the report into individual claims, then checks each
  claim against the sources. Score = supported claims / all claims. Compare
  it with judge.py's single 1-5 "groundedness" guess.
- Context relevance: grades whether the *search results* are relevant to the
  topic. This scores the researcher agent, which nothing else in our evals does.

Both use an LLM, so they cost API calls: about 4 per report. Ragas is an optional
dependency group: `uv sync --group evals`.
"""
import asyncio
import math
import re

from app import config

RAGAS_THRESHOLDS = {
    "ragas_faithfulness": 0.8,       # at least 80% of claims supported by the sources
    "ragas_context_relevance": 0.5,  # search results mostly on topic (0, 0.5 or 1 per grader)
}


def split_contexts(data: str) -> list[str]:
    """The research node joins sources as "[1] title (url)\\ntext\\n\\n[2] ...";
    Ragas wants them as a list, one context per source."""
    return [block.strip() for block in re.split(r"\n\n(?=\[\d+\] )", data or "") if block.strip()]


def build_llm(model: str | None = None):
    """Gemini, wrapped the way Ragas expects.

    Ragas metrics are async, but its own llm_factory() wraps google-genai
    clients in sync mode, so we build the async Instructor wrapper ourselves.
    """
    import instructor
    from google import genai
    from ragas.llms.base import InstructorLLM, InstructorModelArgs

    client = genai.Client(api_key=config.require("GEMINI_API_KEY"))
    return InstructorLLM(
        client=instructor.from_genai(client, use_async=True),
        model=model or config.JUDGE_MODEL_NAME,
        provider="google",
        # Ragas' default of 1024 output tokens is too small to list every claim in a full report
        model_args=InstructorModelArgs(max_tokens=8192),
    )


async def _score(llm, topic: str, report: str, contexts: list[str]):
    from ragas.metrics.collections import ContextRelevance, Faithfulness

    return await asyncio.gather(
        Faithfulness(llm=llm).ascore(user_input=topic, response=report, retrieved_contexts=contexts),
        ContextRelevance(llm=llm).ascore(user_input=topic, retrieved_contexts=contexts),
        return_exceptions=True,  # one failing metric shouldn't lose the other's score
    )


def ragas_scores(topic: str, report: str, data: str, llm=None) -> dict:
    """Return {"ragas_faithfulness": float|None, "ragas_context_relevance": float|None, "errors": [...]}."""
    try:
        import ragas  # noqa: F401
    except ImportError:
        return {"errors": ["ragas is not installed; run `uv sync --group evals`"]}

    contexts = split_contexts(data)
    if not contexts:
        return {"errors": ["no source contexts to evaluate against"]}

    results = asyncio.run(_score(llm or build_llm(), topic, report, contexts))

    scores, errors = {}, []
    for name, result in zip(RAGAS_THRESHOLDS, results):
        if isinstance(result, Exception):
            scores[name] = None
            errors.append(f"{name}: {type(result).__name__}: {str(result)[:200]}")
        else:
            # Ragas returns NaN when it can't score (e.g. no claims found)
            value = result.value
            scores[name] = None if value is None or math.isnan(value) else round(value, 3)
    scores["errors"] = errors
    return scores


def failed_ragas(scores: dict, thresholds: dict = RAGAS_THRESHOLDS) -> list[str]:
    failures = [f"ragas error: {e}" for e in scores.get("errors", [])]
    failures += [
        f"{name} {scores[name]} < {minimum}"
        for name, minimum in thresholds.items()
        if scores.get(name) is not None and scores[name] < minimum
    ]
    return failures
