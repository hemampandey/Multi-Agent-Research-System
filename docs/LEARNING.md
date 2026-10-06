# Learning Guide: Harness, Guardrails & Evaluations

This guide walks through the three reliability layers added to this project. The order is deliberate: **harness → guardrails → evals**. Each layer depends on the one before it.

---

## 1. The Harness: making the system controllable

**Problem:** the agents called Gemini and Tavily directly. Every run cost money, took about 10 seconds, gave a different answer each time, and needed API keys. You can't test "what happens when the critic rejects 5 times?" if you can't *make* the critic reject.

**Idea: dependency injection.** Agents still call `generate(prompt)` and `search_web(query)`, but *which* backend answers is decided at runtime:

```python
from app.harness.runner import run_research
from app.harness.fakes import FakeLLM, FakeSearch

result = run_research(
    "Solid-state batteries",
    llm=FakeLLM(critic="REJECT: needs more depth"),   # script one agent's behavior
    search=FakeSearch(per_query=2),
)
print(result.revision_count, result.trace["summary"])
```

| File | What to look at |
|---|---|
| [app/llm.py](../app/llm.py) | `use_llm()` swaps the backend via a `ContextVar`. `LLMError` replaces the old `"LLM failed"` string. |
| [app/harness/tracing.py](../app/harness/tracing.py) | `@traced` records each node's time/outcome; `generate()` logs each LLM call |
| [app/harness/fakes.py](../app/harness/fakes.py) | `FakeLLM` works out which agent is calling from the prompt text and returns scripted answers |
| [app/harness/runner.py](../app/harness/runner.py) | `run_research()`, the one entry point shared by UI, CLI, tests and evals |
| [tests/conftest.py](../tests/conftest.py) | Blocks real APIs in tests, so a forgotten fake fails instead of spending money |

**Why a ContextVar and not a global?** It's scoped to a `with` block and is restored afterwards, even on exceptions. LangGraph copies the context into the nodes it runs, so the swap reaches every agent.

**Try it:**
1. Run `uv run python -m app.main "CRISPR" --mode Basic`, then open the JSON in `runs/`. Which node took the longest?
2. Write a test where the planner returns garbage (`FakeLLM(planner="")`). What does the pipeline do? (Hint: `planner.unparseable`.)

---

## 2. Guardrails: checking at every trust boundary

**Prompts ask; guardrails verify.** A prompt saying "only cite real sources" makes good behavior *likely*. A code check makes bad behavior *visible and fixable*.

```
topic ─▶ [input guard] ─▶ planner ─▶ search ─▶ [content guard] ─▶ writer ⇄ critic ─▶ [output guard] ─▶ user
          BLOCK                                  SANITIZE                             REPAIR / FLAG
```

| Boundary | Threat | File |
|---|---|---|
| User input | Direct prompt injection ("ignore previous instructions…"), harmful topics, empty or huge input | [app/guardrails/input.py](../app/guardrails/input.py) |
| Web content | *Indirect* prompt injection: a web page containing instructions aimed at your LLM | [app/guardrails/content.py](../app/guardrails/content.py) + the `<sources>` wrapper in [writer.py](../app/agents/writer.py) |
| Agent ↔ agent | Critic ignoring the ACCEPT/REJECT protocol, or "polishing" away all citations | `critic_node` in [app/graph.py](../app/graph.py) |
| Final output | Hallucinated citations (`[7]` with 5 sources), leaked PII, protocol leaks | [app/guardrails/output.py](../app/guardrails/output.py) |
| Cost | Runaway loops or retries | `BudgetExceeded` in [app/llm.py](../app/llm.py) |

Two outcome styles, chosen per risk:
- **Block** (`GuardrailViolation`): stop before spending tokens, or when there are no sources to ground on. *Fail closed.*
- **Repair/flag** (`guardrail_events`): fix what's safe to fix, record everything. The UI shows warnings and evals count interventions.

**A bug the guardrails exposed:** the old research node numbered data blocks *per question* and shuffled sources with `set()`, so `[2]` in the report pointed at a random URL. Now each source gets its own stable number. See `test_citations_map_to_sources`.

**Limits to know:** regex filters are easy to evade, and they also produce false positives. Look at `test_legitimate_topics_pass`: "History of the atomic bomb" must still be allowed. Real systems add a moderation model, but the block / repair / record shape stays the same.

### Case study: the injection that got through

The first version of the input check matched only a few exact phrasings. "Ignore all previous instructions" was blocked, but "ignore *your* instructions", "Forget all previous instructions" and "Act as DAN" were not: **3 of 16 attacks caught**. The fix shows the standard pattern:

1. **Layer 1, broader regex** ([input.py](../app/guardrails/input.py)): free and instant. It now catches 14 of the 16, while tests confirm real topics like "How enzymes act as catalysts" still pass. Patterns that are only suspicious in a topic ("respond with") are kept out of the web-content filter, because articles use them innocently.
2. **Layer 2, LLM classifier** ([classifier.py](../app/guardrails/classifier.py)): judges *intent*, so it catches rephrasings no pattern predicts. It runs only after layer 1 passes, so obvious attacks cost nothing.
3. **Tests vs evals:** the pytest cases use a *fake* classifier, so they prove the wiring. Eval cases marked `requires_llm` prove that *real Gemini* classifies correctly.

A real eval run then showed layer 3 working too. Researching "Prompt injection attacks" pulled in articles that quote example attacks, and `content.removed_injection` removed those lines before the writer saw them.

**Try it:**
1. Add a guardrail that flags reports where one source is cited for more than 60% of all citations ("single-source bias"). Write the test first.
2. Find a phrasing that gets past `INJECTION_RE`, add it to the test's parametrize list, then fix the pattern.

---

## 3. Evaluations: measuring quality so changes are comparable

**Tests vs evals:** tests ask "does the code behave correctly?" (pass/fail, deterministic, fake LLM). Evals ask "how *good* are the outputs?" (scores, real LLM, run on a dataset, compared over time).

| File | Role |
|---|---|
| [evals/dataset.jsonl](../evals/dataset.jsonl) | Cases: real topics with `must_mention` keywords, plus guardrail cases with `expect_blocked` |
| [evals/metrics.py](../evals/metrics.py) | Code-based scores: citation validity, density, source coverage, structure, keyword recall |
| [evals/judge.py](../evals/judge.py) | LLM-as-judge: groundedness / relevance / coherence on an anchored 1–5 rubric, returned as JSON |
| [evals/run_evals.py](../evals/run_evals.py) | Runs cases, applies thresholds, saves to `evals/results/`, prints the change vs the previous run |

Key ideas in the code:
- **Use cheap checks first.** Anything code can check (citation numbers, headings) shouldn't cost a judge call.
- **Measure before the guardrail.** `citation_validity` uses `raw_report`, because the output guard strips bad citations and would otherwise hide the model's mistakes.
- **Judges are models too.** They're noisy, biased toward their own writing (set `JUDGE_MODEL_NAME`), and sometimes return broken JSON (`parse_judgement` handles it).
- **Regression tracking.** The useful number is the *change* after you edit a prompt, not the absolute score.

**Try it (the core eval workflow):**
1. Run `uv run python -m evals.run_evals` to get a baseline.
2. Change one thing, e.g. remove "Never invent a citation" from `SOURCE_RULES` in writer.py, or switch `MODEL_NAME`.
3. Re-run and read the change lines. Did `citation_validity` or `judge_groundedness` move?
4. Add 3–5 topics from your own domain to the dataset. A good eval set covers the inputs your real users send.
5. Rate 5 reports yourself 1–5, then compare with the judge. If you disagree a lot, improve the rubric before trusting it.

---

## Where to go next

- Run `pytest` and `evals --offline` in GitHub Actions on every push.
- Add an `expected_sources_min` field to cases and an eval for search quality.
- Add LangSmith or OpenTelemetry tracing in place of the JSON traces.
- Swap the regex input guard for a moderation model, and keep the same tests.
