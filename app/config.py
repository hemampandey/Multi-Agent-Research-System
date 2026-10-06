import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash-lite")
# The evals' LLM-as-judge. Ideally a different (stronger) model than the one
# being graded, because models tend to rate their own writing too kindly.
JUDGE_MODEL_NAME = os.getenv("JUDGE_MODEL_NAME", MODEL_NAME)

# Pipeline limits
MAX_QUESTIONS = 3            # planner sub-questions used in Advanced mode
MAX_REVISIONS = 2            # critic rejections before we ship the latest draft (= max drafts)
MAX_LLM_CALLS_PER_RUN = 12   # cost guardrail; a normal run uses at most 6
MAX_SOURCE_CHARS = 1500      # per search result, after sanitizing

_KEY_HINTS = {
    "GEMINI_API_KEY": "Please generate a key from Google AI Studio and configure it.",
    "TAVILY_API_KEY": "Please generate a search API key from Tavily and configure it.",
}


def require(name: str) -> str:
    """Return a required secret, failing with a helpful message if it's missing.

    Checked lazily (when a real service is first called) rather than at import
    time, so tests and offline evals can run without any API keys.
    """
    value = os.getenv(name)
    if not value:
        raise ValueError(
            f"Missing {name} in environment variables or .env file. "
            f"{_KEY_HINTS.get(name, '')}"
        )
    return value
