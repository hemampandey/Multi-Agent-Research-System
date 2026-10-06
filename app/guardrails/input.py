"""Input guardrails: validate the user's topic before spending any tokens on it.

These regexes are a teaching baseline, not a complete defense. Production
systems usually add a moderation model or classifier on top; the shape stays
the same (normalize → check → block with a reason code).
"""
import re
import unicodedata

from app.guardrails import GuardrailViolation

MIN_TOPIC_CHARS = 3
MAX_TOPIC_CHARS = 200
MODES = ("Basic", "Advanced")

# Layer 1 against direct prompt injection: the user trying to override our
# instructions. Fast and free, but it only matches wordings we thought of,
# so classifier.py adds an LLM check as layer 2.
# Each pattern is kept narrow on purpose: "How enzymes act as catalysts" or
# "Senate rules on filibusters" must still pass (see tests).
INJECTION_PATTERNS = [
    # ignore / forget / disregard / override + (your|previous|...) instructions
    r"\b(ignore|forget|disregard|override)\s+(all\s+|any\s+|of\s+)*"
    r"(your|the|my|these|those|previous|prior|above|earlier)?\s*"
    r"(previous\s+|prior\s+|above\s+|earlier\s+|system\s+)?(instructions?|directions?|guidelines|prompts?)\b",
    r"\b(ignore|forget|disregard|override)\s+(all\s+)?(your|previous|prior|the\s+above)\s+rules\b",
    r"\b(ignore|disregard)\s+(the\s+)?(instructions?|directions?|rules)\s+above\b",
    r"\bnew\s+instructions?\s*:",
    r"(reveal|print|show|repeat)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions)",
    r"\byour\s+system\s+prompt\b",
    r"\bjailbreak\b",
    r"</?\s*(system|assistant|instructions?)\s*>",
]
# Only suspicious in a *topic*. Web pages say "respond with" or "you are now"
# innocently, so content.py uses INJECTION_RE without these.
TOPIC_ONLY_PATTERNS = [
    r"\bforget\s+everything\b",
    r"\b(instead\s+of|do\s+not|don'?t)\s+(writ(e|ing)\s+)?(a|the)\s+report\b",
    r"\bpretend\s+(you\s+are|to\s+be|you'?re)\b",
    r"\byou\s+are\s+now\b",
    r"\b(output|reply|respond)\s+(only|with)\b|\bjust\s+say\b",
]
INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS), re.IGNORECASE)
TOPIC_INJECTION_RE = re.compile("|".join(INJECTION_PATTERNS + TOPIC_ONLY_PATTERNS), re.IGNORECASE)

# Topics we refuse to research at all.
BLOCKED_TOPIC_RE = re.compile(
    r"\b(make|build|synthesi[sz]e|manufacture|produce)\b.*"
    r"\b(bombs?|explosives?|nerve\s+agents?|bioweapons?|chemical\s+weapons?|meth(amphetamine)?)\b",
    re.IGNORECASE,
)


def validate_topic(raw: str | None) -> str:
    """Return a cleaned topic, or raise GuardrailViolation with a reason code."""
    topic = unicodedata.normalize("NFKC", raw or "")
    # Replace control characters (newlines, zero-width tricks, ...) with spaces
    topic = "".join(ch if ch.isprintable() else " " for ch in topic)
    topic = re.sub(r"\s+", " ", topic).strip()

    if len(topic) < MIN_TOPIC_CHARS:
        raise GuardrailViolation("topic_too_short", "Please enter a research topic.")
    if len(topic) > MAX_TOPIC_CHARS:
        raise GuardrailViolation(
            "topic_too_long", f"Topic must be at most {MAX_TOPIC_CHARS} characters."
        )
    if TOPIC_INJECTION_RE.search(topic):
        raise GuardrailViolation(
            "prompt_injection", "The topic looks like an attempt to override the assistant's instructions."
        )
    if BLOCKED_TOPIC_RE.search(topic):
        raise GuardrailViolation("blocked_topic", "This topic is not something this assistant will research.")
    return topic


def validate_mode(mode: str | None) -> str:
    mode = mode or "Advanced"
    if mode not in MODES:
        raise GuardrailViolation("invalid_mode", f"Mode must be one of {MODES}.")
    return mode
