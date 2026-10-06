"""Guardrails: deterministic checks at every trust boundary of the pipeline.

    user topic ──▶ input.py   ──▶ planner ─▶ search ──▶ content.py ──▶ writer ─▶ critic ──▶ output.py ──▶ user
                  (block)                             (sanitize)                         (repair/flag)

Two kinds of outcome:
- **Block**: raise GuardrailViolation; the run stops (bad input, nothing to ground on).
- **Repair/flag**: fix the text or annotate it, and record a guardrail event
  so the UI, traces and evals can see what was intervened on.

Prompts *ask* the model to behave; guardrails *check* that it did. You want both.
"""


class GuardrailViolation(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def event(guard: str, action: str, detail: str = "") -> dict:
    return {"guard": guard, "action": action, "detail": detail}
