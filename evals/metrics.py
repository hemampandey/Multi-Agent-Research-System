"""Deterministic metrics: fast, free, and the same every time.

Use code-based checks for everything code *can* check, and save the
LLM judge for the rest. All scores are 0-1, where higher is better.
"""
import re

from app.guardrails.output import find_citations

SECTIONS = {
    "introduction": r"introduction|overview",
    "key points": r"key\s+(points|findings)|main\s+points",
    "conclusion": r"conclusions?|summary",
}

# Minimum score for a case to pass. Tune these as you learn what "good" looks like.
THRESHOLDS = {
    "citation_validity": 1.0,   # every citation in the model's output points at a real source
    "citation_density": 0.6,    # most substantive paragraphs carry a citation
    "source_coverage": 0.3,     # the report actually uses the research it was given
    "structure": 1.0,           # intro, key points and conclusion are all present
    "keyword_recall": 0.5,      # mentions the concepts a good report must cover
}


def citation_validity(report: str, num_sources: int) -> float:
    cites = find_citations(report)
    if not cites:
        return 0.0
    return sum(1 <= c <= num_sources for c in cites) / len(cites)


def citation_density(report: str) -> float:
    blocks = [b.strip() for b in re.split(r"\n\s*\n|\n(?=\s*[-*•] )", report)]
    substantive = [b for b in blocks if len(b.split()) >= 12 and not b.startswith("#")]
    if not substantive:
        return 0.0
    return sum(bool(find_citations(b)) for b in substantive) / len(substantive)


def source_coverage(report: str, num_sources: int) -> float:
    if not num_sources:
        return 0.0
    used = {c for c in find_citations(report) if 1 <= c <= num_sources}
    return len(used) / num_sources


def structure(report: str) -> float:
    found = sum(
        bool(re.search(rf"^\s*(#+\s*|\*\*)?\s*(\d+\.\s*)?({pattern})\b", report, re.IGNORECASE | re.MULTILINE))
        for pattern in SECTIONS.values()
    )
    return found / len(SECTIONS)


def keyword_recall(report: str, keywords: list[str]) -> float | None:
    if not keywords:
        return None
    text = report.lower()
    return sum(k.lower() in text for k in keywords) / len(keywords)


def score_report(report: str, sources: list[str], must_mention: list[str] = (),
                 raw_report: str | None = None) -> dict:
    """`raw_report` is the text before output guardrails; citation validity is
    measured on it, because the guardrail strips bad citations from `report`
    and would hide the model's mistakes."""
    n = len(sources)
    return {
        "citation_validity": round(citation_validity(raw_report or report, n), 3),
        "citation_density": round(citation_density(report), 3),
        "source_coverage": round(source_coverage(report, n), 3),
        "structure": round(structure(report), 3),
        "keyword_recall": keyword_recall(report, list(must_mention)),
        "word_count": len(report.split()),
    }


def failed_checks(scores: dict, thresholds: dict = THRESHOLDS) -> list[str]:
    return [
        f"{name} {scores[name]} < {minimum}"
        for name, minimum in thresholds.items()
        if scores.get(name) is not None and scores[name] < minimum
    ]
