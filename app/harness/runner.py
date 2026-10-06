"""`run_research()`: the single, observable way to run the pipeline.

Everything (Streamlit, CLI, tests, evals) goes through here, so they all get:
- **Injection**: pass `llm=` / `search=` to swap real services for fakes or other models.
- **Tracing**: every node and LLM call is recorded in `result.trace`.
- **Clean failures**: guardrail blocks and LLM outages become `result.error_code`
  instead of exceptions, so callers can show or score them.
- **Artifacts**: `save_dir=` writes the whole run to JSON for later inspection.
"""
import json
import re
from contextlib import ExitStack
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from app.graph import graph
from app.guardrails import GuardrailViolation
from app.harness.tracing import Trace, tracing
from app.llm import LLMBackend, LLMError, use_llm
from app.tools.search import SearchBackend, use_search


@dataclass
class RunResult:
    topic: str
    mode: str
    final_report: str = ""
    raw_report: str = ""
    sources: list[str] = field(default_factory=list)
    questions: list[str] = field(default_factory=list)
    data: str = ""
    revision_count: int = 0
    guardrail_events: list[dict] = field(default_factory=list)
    trace: dict = field(default_factory=dict)
    error: str | None = None
    error_code: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None

    def to_dict(self) -> dict:
        return asdict(self)


def run_research(
    topic: str,
    mode: str = "Advanced",
    *,
    llm: LLMBackend | None = None,
    search: SearchBackend | None = None,
    save_dir: str | Path | None = None,
) -> RunResult:
    trace = Trace()
    result = RunResult(topic=topic, mode=mode)

    with ExitStack() as stack:
        if llm is not None:
            stack.enter_context(use_llm(llm))
        if search is not None:
            stack.enter_context(use_search(search))
        stack.enter_context(tracing(trace))

        try:
            state = graph.invoke({"topic": topic, "mode": mode})
            result = RunResult(
                topic=state["topic"],
                mode=state["mode"],
                final_report=state["final_report"],
                raw_report=state.get("raw_report", ""),
                sources=state["sources"],
                questions=state["questions"],
                data=state["data"],
                revision_count=state.get("revision_count", 0),
                guardrail_events=state.get("guardrail_events", []),
            )
        except GuardrailViolation as e:
            result.error, result.error_code = str(e), e.code
        except LLMError as e:
            result.error, result.error_code = str(e), e.code

    result.trace = trace.to_dict()
    if save_dir is not None:
        save_run(result, save_dir)
    return result


def save_run(result: RunResult, save_dir: str | Path) -> Path:
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", result.topic.lower()).strip("-")[:40] or "run"
    path = save_dir / f"{datetime.now():%Y%m%d-%H%M%S}_{slug}.json"
    path.write_text(json.dumps(result.to_dict(), indent=2))
    return path
