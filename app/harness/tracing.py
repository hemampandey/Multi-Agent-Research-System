"""Tracing: a record of what happened inside one pipeline run.

A multi-agent system is hard to debug from its final answer alone. When an
eval fails you want to know *where*: did the planner produce bad questions,
did search return nothing, did the critic loop three times? A trace answers
that by recording a span per graph node and an entry per LLM call.

The active trace lives in a ContextVar, so agents don't need a trace passed
in. `generate()` just asks "is anyone tracing right now?" and logs if so.
"""
import functools
import time
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import asdict, dataclass, field


@dataclass
class Span:
    name: str
    duration_s: float = 0.0
    ok: bool = True
    error: str | None = None
    output_keys: list[str] = field(default_factory=list)


@dataclass
class LLMCall:
    node: str | None
    duration_s: float
    prompt_chars: int
    response_chars: int
    ok: bool
    error: str | None = None


@dataclass
class Trace:
    spans: list[Span] = field(default_factory=list)
    llm_calls: list[LLMCall] = field(default_factory=list)
    current_node: str | None = None

    def summary(self) -> dict:
        return {
            "nodes": [s.name for s in self.spans],
            "total_s": round(sum(s.duration_s for s in self.spans), 2),
            "llm_calls": len(self.llm_calls),
            "llm_failures": sum(not c.ok for c in self.llm_calls),
            "prompt_chars": sum(c.prompt_chars for c in self.llm_calls),
        }

    def to_dict(self) -> dict:
        return {
            "summary": self.summary(),
            "spans": [asdict(s) for s in self.spans],
            "llm_calls": [asdict(c) for c in self.llm_calls],
        }


_current: ContextVar[Trace | None] = ContextVar("trace", default=None)


def current_trace() -> Trace | None:
    return _current.get()


@contextmanager
def tracing(trace: Trace):
    token = _current.set(trace)
    try:
        yield trace
    finally:
        _current.reset(token)


def traced(name: str):
    """Decorator for graph nodes: records duration, outcome and returned keys."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state):
            trace = _current.get()
            if trace is None:
                return fn(state)

            span = Span(name=name)
            trace.spans.append(span)
            trace.current_node = name
            start = time.perf_counter()
            try:
                output = fn(state)
                span.output_keys = sorted(output or {})
                return output
            except Exception as e:
                span.ok = False
                span.error = f"{type(e).__name__}: {e}"
                raise
            finally:
                span.duration_s = round(time.perf_counter() - start, 3)
                trace.current_node = None
        return wrapper
    return decorator


def record_llm_call(duration_s: float, prompt: str, response: str = "", error: str | None = None):
    trace = _current.get()
    if trace is None:
        return
    trace.llm_calls.append(LLMCall(
        node=trace.current_node,
        duration_s=round(duration_s, 3),
        prompt_chars=len(prompt),
        response_chars=len(response),
        ok=error is None,
        error=error,
    ))
