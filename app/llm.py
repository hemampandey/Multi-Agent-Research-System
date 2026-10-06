"""Single access point to the LLM for every agent.

Agents call `generate(prompt)`. *Which* model answers is decided by the active
backend: Gemini by default, swappable at runtime with `use_llm(...)`. That
one indirection is what lets the harness run the whole pipeline against a
scripted fake (tests) or a different model (judge, A/B comparisons).
"""
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable

from app import config
from app.harness.tracing import current_trace, record_llm_call

LLMBackend = Callable[[str], str]

RETRY_BACKOFF_SECONDS = 2.0


class LLMError(RuntimeError):
    """The model could not produce an answer.

    Raised rather than returning an error string, so a failure message can
    never flow downstream and get "polished" into a report.
    """
    code = "llm_error"


class BudgetExceeded(LLMError):
    """Cost guardrail: this run already made too many LLM calls."""
    code = "budget_exceeded"


_client = None


def gemini_backend(prompt: str, model: str | None = None) -> str:
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=config.require("GEMINI_API_KEY"))

    response = _client.models.generate_content(
        model=model or config.MODEL_NAME,
        contents=prompt,
    )
    if not response.text:
        raise LLMError("Model returned an empty response")
    return response.text


_active: ContextVar[LLMBackend] = ContextVar("llm_backend", default=gemini_backend)


@contextmanager
def use_llm(backend: LLMBackend):
    """Route every `generate()` call inside this block to `backend`."""
    token = _active.set(backend)
    try:
        yield backend
    finally:
        _active.reset(token)


def generate(prompt: str, retries: int = 3) -> str:
    trace = current_trace()
    if trace is not None and len(trace.llm_calls) >= config.MAX_LLM_CALLS_PER_RUN:
        raise BudgetExceeded(
            f"Run exceeded {config.MAX_LLM_CALLS_PER_RUN} LLM calls; stopping to cap cost."
        )

    backend = _active.get()
    last_error = None
    for attempt in range(1, retries + 1):
        start = time.perf_counter()
        try:
            text = backend(prompt)
            record_llm_call(time.perf_counter() - start, prompt, text)
            return text
        except Exception as e:
            last_error = e
            record_llm_call(time.perf_counter() - start, prompt, error=f"{type(e).__name__}: {e}")
            print(f"[LLM ERROR] Attempt {attempt}: {e}")
            if attempt < retries:
                time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    raise LLMError(f"LLM failed after {retries} attempts: {last_error}") from last_error
