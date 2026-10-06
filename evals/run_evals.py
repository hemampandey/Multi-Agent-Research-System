"""Run the eval suite.

    python -m evals.run_evals                 # real Gemini + Tavily (costs API calls)
    python -m evals.run_evals --offline       # fakes: checks the eval plumbing for free
    python -m evals.run_evals --no-judge      # skip the LLM-as-judge
    python -m evals.run_evals --only rag-basics guard-injection

Each run is saved to evals/results/ and compared with the previous one, so you
can see whether a prompt or code change made things better or worse.
Exits non-zero if any case fails, so it can gate CI.
"""
import argparse
import functools
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

from app import config
from app.harness.fakes import FakeLLM, FakeSearch
from app.harness.runner import run_research
from app.llm import gemini_backend
from evals.judge import failed_judgements, judge_report
from evals.metrics import failed_checks, score_report

EVALS_DIR = Path(__file__).parent
RESULTS_DIR = EVALS_DIR / "results"


def load_cases(path: Path = EVALS_DIR / "dataset.jsonl") -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def run_case(case: dict, *, offline: bool = False, use_judge: bool = True) -> dict:
    llm, search = (FakeLLM(), FakeSearch()) if offline else (None, None)
    result = run_research(case["topic"], case.get("mode", "Advanced"), llm=llm, search=search)

    record = {
        "id": case["id"],
        "topic": case["topic"],
        "error_code": result.error_code,
        "trace": result.trace["summary"],
    }

    # Guardrail cases: success means the run was blocked for the right reason
    if "expect_blocked" in case:
        passed = result.error_code == case["expect_blocked"]
        record.update(kind="guardrail", passed=passed, failures=[] if passed else [
            f"expected block '{case['expect_blocked']}', got {result.error_code or 'no block'}"
        ])
        return record

    record["kind"] = "quality"
    if not result.ok:
        record.update(passed=False, failures=[f"run failed ({result.error_code}): {result.error}"])
        return record

    # Fake reports can't contain topic-specific keywords, so skip that check offline
    must_mention = [] if offline else case.get("must_mention", [])
    scores = score_report(result.final_report, result.sources, must_mention, raw_report=result.raw_report)
    scores["revisions"] = result.revision_count
    scores["guardrail_events"] = len(result.guardrail_events)
    failures = failed_checks(scores)

    if use_judge:
        judge_llm = FakeLLM() if offline else functools.partial(gemini_backend, model=config.JUDGE_MODEL_NAME)
        judgement = judge_report(result.topic, result.final_report, result.data, llm=judge_llm)
        record["judge"] = judgement
        failures += failed_judgements(judgement)
        if "error" not in judgement:
            for name, item in judgement.items():
                scores[f"judge_{name}"] = item["score"]

    record.update(scores=scores, passed=not failures, failures=failures)
    return record


def summarize(records: list[dict]) -> dict:
    summary = {"cases": len(records), "passed": sum(r["passed"] for r in records)}
    quality = [r for r in records if "scores" in r]
    metric_names = sorted({k for r in quality for k, v in r["scores"].items() if isinstance(v, (int, float))})
    for name in metric_names:
        values = [r["scores"][name] for r in quality if isinstance(r["scores"].get(name), (int, float))]
        summary[f"mean_{name}"] = round(statistics.mean(values), 3)
    return summary


def print_report(records: list[dict], summary: dict, previous: dict | None):
    print(f"\n{'case':<28} {'result':<7} {'llm':>4} {'secs':>6}  notes")
    print("-" * 90)
    for r in records:
        status = "PASS" if r["passed"] else "FAIL"
        notes = "; ".join(r["failures"]) or (f"blocked: {r['error_code']}" if r["kind"] == "guardrail" else "")
        print(f"{r['id']:<28} {status:<7} {r['trace']['llm_calls']:>4} {r['trace']['total_s']:>6}  {notes}")

    print(f"\nPassed {summary['passed']}/{summary['cases']}")
    for key, value in summary.items():
        if not key.startswith("mean_"):
            continue
        delta = ""
        if previous and key in previous:
            change = round(value - previous[key], 3)
            delta = f"  ({'+' if change >= 0 else ''}{change} vs previous)"
        print(f"  {key:<32} {value}{delta}")


def latest_summary() -> dict | None:
    files = sorted(RESULTS_DIR.glob("*.json"))
    return json.loads(files[-1].read_text())["summary"] if files else None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true", help="use fake LLM and search")
    parser.add_argument("--no-judge", action="store_true", help="skip LLM-as-judge scoring")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these case ids")
    args = parser.parse_args(argv)

    cases = load_cases()
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]

    records = []
    for case in cases:
        print(f"running {case['id']} ...", flush=True)
        records.append(run_case(case, offline=args.offline, use_judge=not args.no_judge))

    summary = summarize(records)
    # Offline runs aren't comparable with real ones, so they're not saved
    previous = None if args.offline else latest_summary()
    print_report(records, summary, previous)

    if not args.offline:
        RESULTS_DIR.mkdir(exist_ok=True)
        path = RESULTS_DIR / f"{datetime.now():%Y%m%d-%H%M%S}.json"
        path.write_text(json.dumps({
            "summary": summary,
            "model": config.MODEL_NAME,
            "judge_model": config.JUDGE_MODEL_NAME,
            "records": records,
        }, indent=2))
        print(f"\nSaved {path}")

    return 0 if summary["passed"] == summary["cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
