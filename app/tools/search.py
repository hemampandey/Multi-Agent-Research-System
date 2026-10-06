"""Web search tool. Same swappable-backend pattern as app.llm (see `use_search`)."""
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Callable

import requests

from app import config

SearchBackend = Callable[[str], dict]


def tavily_search(query: str, max_results: int = 3) -> dict:
    response = requests.post(
        "https://api.tavily.com/search",
        json={
            "api_key": config.require("TAVILY_API_KEY"),
            "query": query,
            "max_results": max_results,
        },
        timeout=10,  # avoid hanging indefinitely
    )
    response.raise_for_status()
    return response.json()


_active: ContextVar[SearchBackend] = ContextVar("search_backend", default=tavily_search)


@contextmanager
def use_search(backend: SearchBackend):
    """Route every `search_web()` call inside this block to `backend`."""
    token = _active.set(backend)
    try:
        yield backend
    finally:
        _active.reset(token)


def search_web(query: str) -> dict:
    try:
        return _active.get()(query)
    except Exception as e:
        print(f"[SEARCH ERROR] Failed searching web for '{query}': {e}")
        # Graceful fallback; the research node decides what "no results" means
        return {"results": []}
