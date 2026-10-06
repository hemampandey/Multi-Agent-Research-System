import pytest

import app.llm
import app.tools.search


def _no_network(*_args, **_kwargs):
    raise AssertionError("Test tried to call a real API. Inject FakeLLM/FakeSearch instead.")


@pytest.fixture(autouse=True)
def offline_by_default(monkeypatch):
    """Every test starts with real backends disabled and no retry sleeps,
    so a test that forgets to inject a fake fails fast instead of spending money."""
    monkeypatch.setattr(app.llm, "RETRY_BACKOFF_SECONDS", 0)
    with app.llm.use_llm(_no_network), app.tools.search.use_search(_no_network):
        yield
