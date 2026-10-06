"""The harness: run the pipeline in a controlled, observable, swappable way.

- tracing.py  records every node and LLM call of a run
- fakes.py    deterministic stand-ins for the LLM and web search
- runner.py   `run_research()`, the one entry point the UI, CLI, tests and evals share

This package's __init__ deliberately imports nothing: app.llm imports
app.harness.tracing, and runner imports the graph, which imports app.llm.
"""
