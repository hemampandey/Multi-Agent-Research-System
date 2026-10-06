"""Content guardrails: treat web search results as untrusted data.

Indirect prompt injection is the big risk for research agents: a web page can
contain text like "ignore previous instructions and ..." that ends up inside
the writer's prompt. We defend in two layers:
1. Here, in code: strip markup, drop instruction-like lines, cap length.
2. In the writer prompt: wrap sources in <sources> tags and say they are data.
"""
import re
from urllib.parse import urlparse

from app import config
from app.guardrails.input import INJECTION_RE

_HTML_TAG_RE = re.compile(r"<[^>]{1,200}>")


def is_allowed_url(url: str) -> bool:
    parsed = urlparse(url or "")
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def sanitize_source_text(text: str, max_chars: int | None = None) -> tuple[str, list[str]]:
    """Return (clean_text, flags). Flags name each intervention that happened."""
    max_chars = max_chars or config.MAX_SOURCE_CHARS
    flags = []

    text = _HTML_TAG_RE.sub(" ", text or "")

    kept = []
    for line in text.splitlines():
        if INJECTION_RE.search(line):
            flags.append("removed_injection")
            continue
        kept.append(line)
    text = "\n".join(kept).strip()

    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"
        flags.append("truncated")

    return text, flags
