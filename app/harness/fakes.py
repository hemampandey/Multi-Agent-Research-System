"""Deterministic stand-ins for the LLM and web search.

With these plugged in, the full graph runs in milliseconds, for free,
offline, and gives the same answer every time. That's what makes it possible
to write tests like "if the critic always rejects, the loop still stops".

    llm = FakeLLM(critic="REJECT: add citations")   # override one role
    llm = FakeLLM(critic=["REJECT: more", "ACCEPT: ..."])  # answers in order
    llm = FakeLLM(writer=LLMError("boom"))         # simulate a failure
"""
import json
import re


def good_report(topic: str, num_sources: int = 4) -> str:
    """A well-formed report that only cites sources 1..num_sources."""
    def c(i):
        return min(i, max(num_sources, 1))

    return f"""## Introduction
{topic} is an active area of research and practical engineering, and this report summarizes what the retrieved sources say about it [{c(1)}].

## Key Points
- The core idea behind {topic} is described consistently across several of the retrieved sources [{c(1)}, {c(2)}].
- Practitioners report concrete benefits as well as real limitations when applying it in production settings [{c(3)}].
- Ongoing work focuses on reliability, cost, and evaluation, which remain open problems for most teams [{c(2)}, {c(4)}].

## Conclusion
{topic} is promising, but the sources agree that careful evaluation and well-designed safeguards are needed before relying on it [{c(4)}]."""


DEFAULT_JUDGEMENT = json.dumps({
    "groundedness": {"score": 4, "reason": "fake judge"},
    "relevance": {"score": 5, "reason": "fake judge"},
    "coherence": {"score": 4, "reason": "fake judge"},
})


def _topic_of(prompt: str) -> str:
    # Writer/critic prompts contain `topic: "<topic>"`
    if 'topic: "' in prompt:
        return prompt.split('topic: "', 1)[1].split('"', 1)[0]
    return "the topic"


class FakeLLM:
    # Checked in order: the first marker found in the prompt decides the role
    ROLES = {
        "judge": "impartial evaluator",
        "planner": "Break this topic",
        "writer_revise": "You are revising",
        "writer": "Write a professional research report",
        "critic": "expert editor",
    }

    def __init__(self, **responses):
        self.responses = responses
        self.calls: list[tuple[str, str]] = []  # (role, prompt)

    def role_of(self, prompt: str) -> str:
        return next((role for role, marker in self.ROLES.items() if marker in prompt), "unknown")

    def count(self, role: str) -> int:
        return sum(1 for r, _ in self.calls if r == role)

    def _default(self, role: str, prompt: str) -> str:
        if role == "planner":
            return "1. What is it?\n2. Why does it matter?\n3. How is it used today?\n4. What are its limits?"
        if role in ("writer", "writer_revise"):
            num_sources = len(re.findall(r"^\s*\[\d+\] ", prompt, re.MULTILINE))
            return good_report(_topic_of(prompt), num_sources)
        if role == "critic":
            draft = prompt.split("Report to review:", 1)[-1].strip()
            return "ACCEPT:\n" + draft
        if role == "judge":
            return DEFAULT_JUDGEMENT
        return "OK"

    def __call__(self, prompt: str) -> str:
        role = self.role_of(prompt)
        self.calls.append((role, prompt))

        response = self.responses.get(role)
        if response is None and role == "writer_revise":
            response = self.responses.get("writer")
        if isinstance(response, list):
            response = response.pop(0) if len(response) > 1 else response[0]

        if response is None:
            return self._default(role, prompt)
        if isinstance(response, Exception):
            raise response
        if callable(response):
            return response(prompt)
        return response


class FakeSearch:
    """Returns `per_query` distinct results for each query, or fixed `results`."""

    def __init__(self, per_query: int = 2, results: list[dict] | None = None):
        self.per_query = per_query
        self.results = results
        self.queries: list[str] = []

    def __call__(self, query: str) -> dict:
        self.queries.append(query)
        if self.results is not None:
            return {"results": self.results}
        n = len(self.queries)
        return {"results": [
            {
                "title": f"Source {n}.{i}",
                "url": f"https://example.org/{n}/{i}",
                "content": f"Background fact {n}.{i} relevant to: {query}.",
            }
            for i in range(1, self.per_query + 1)
        ]}
