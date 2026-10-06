"""LLM-as-judge: a model grades the report against a rubric.

Useful for qualities code can't measure, such as "is each claim supported by
the sources?". Things to keep in mind:
- Judges are noisy. Use a rubric with anchored scores and ask for reasons.
- Judges favor their own model's writing; set JUDGE_MODEL_NAME to a different one.
- Ask for JSON, then parse defensively: models don't always comply.
- Spot-check the judge against your own ratings before trusting its trend lines.
"""
import json
import re

from app.llm import LLMBackend, LLMError, generate, use_llm

CRITERIA = ("groundedness", "relevance", "coherence")

JUDGE_THRESHOLDS = {"groundedness": 4, "relevance": 4, "coherence": 3}

MAX_SOURCE_CHARS_FOR_JUDGE = 12000

JUDGE_PROMPT = """You are an impartial evaluator grading a research report on the topic: "{topic}".

The report was only allowed to use these sources:
<sources>
{data}
</sources>

<report>
{report}
</report>

Score each criterion from 1 to 5:
- groundedness: 5 = every factual claim is supported by the cited source; 3 = some claims unsupported; 1 = mostly unsupported or contradicts the sources.
- relevance: 5 = squarely answers the topic; 3 = partly off-topic; 1 = not about the topic.
- coherence: 5 = clear structure and flow; 3 = readable but disorganized; 1 = hard to follow.

Respond with ONLY a JSON object, no other text:
{{"groundedness": {{"score": <1-5>, "reason": "<one sentence>"}}, "relevance": {{"score": <1-5>, "reason": "<one sentence>"}}, "coherence": {{"score": <1-5>, "reason": "<one sentence>"}}}}
"""


def parse_judgement(raw: str) -> dict:
    """Return {criterion: {"score": int, "reason": str}}, or {"error": ...}."""
    match = re.search(r"\{.*\}", raw or "", re.DOTALL)  # tolerates ```json fences and chatter
    if not match:
        return {"error": f"no JSON in judge output: {raw[:200]!r}"}
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return {"error": f"invalid JSON from judge: {e}"}

    judgement = {}
    for name in CRITERIA:
        item = parsed.get(name)
        score = item.get("score") if isinstance(item, dict) else item
        if not isinstance(score, int) or not 1 <= score <= 5:
            return {"error": f"bad or missing score for {name}: {item!r}"}
        judgement[name] = {"score": score, "reason": item.get("reason", "") if isinstance(item, dict) else ""}
    return judgement


def judge_report(topic: str, report: str, data: str, llm: LLMBackend | None = None) -> dict:
    prompt = JUDGE_PROMPT.format(topic=topic, report=report, data=data[:MAX_SOURCE_CHARS_FOR_JUDGE])
    try:
        if llm is None:
            return parse_judgement(generate(prompt))
        with use_llm(llm):
            return parse_judgement(generate(prompt))
    except LLMError as e:
        return {"error": str(e)}


def failed_judgements(judgement: dict, thresholds: dict = JUDGE_THRESHOLDS) -> list[str]:
    if "error" in judgement:
        return [f"judge error: {judgement['error']}"]
    return [
        f"judge.{name} {judgement[name]['score']} < {minimum}"
        for name, minimum in thresholds.items()
        if judgement[name]["score"] < minimum
    ]
