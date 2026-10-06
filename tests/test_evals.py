import pytest

from app.harness.fakes import good_report
from evals.judge import failed_judgements, parse_judgement
from evals.metrics import failed_checks, score_report
from evals.run_evals import load_cases, run_case


def test_good_report_scores_well():
    sources = ["https://a", "https://b", "https://c", "https://d"]
    scores = score_report(good_report("Batteries"), sources, must_mention=["batteries", "graphene"])
    assert scores["citation_validity"] == 1.0
    assert scores["structure"] == 1.0
    assert scores["source_coverage"] == 1.0
    assert scores["keyword_recall"] == 0.5
    assert failed_checks(scores) == []


def test_bad_report_fails_checks():
    scores = score_report("Batteries are nice and there is a lot to say about them overall. [9]", ["https://a"])
    failures = " ".join(failed_checks(scores))
    assert "citation_validity" in failures and "structure" in failures


@pytest.mark.parametrize("raw", [
    '{"groundedness": {"score": 4, "reason": "ok"}, "relevance": {"score": 5}, "coherence": {"score": 3}}',
    '```json\n{"groundedness": 4, "relevance": 5, "coherence": 3}\n```',
    'Here you go: {"groundedness": {"score": 4}, "relevance": {"score": 5}, "coherence": {"score": 3}} Thanks!',
])
def test_parse_judgement_tolerates_formats(raw):
    judgement = parse_judgement(raw)
    assert judgement["groundedness"]["score"] == 4
    assert failed_judgements(judgement) == []


@pytest.mark.parametrize("raw", ["no json here", '{"groundedness": 9}', "{not json}"])
def test_parse_judgement_reports_errors(raw):
    assert "error" in parse_judgement(raw)


def test_every_dataset_case_passes_offline():
    """The eval machinery itself works end to end on every case."""
    for case in load_cases():
        if case.get("requires_llm"):
            continue
        record = run_case(case, offline=True)
        assert record["passed"], (case["id"], record["failures"])
