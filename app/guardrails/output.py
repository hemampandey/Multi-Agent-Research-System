"""Output guardrails: check (and where safe, repair) the final report.

- Citations must point at a real source: `[7]` with only 5 sources is a
  hallucinated citation, so it is removed.
- Protocol leaks such as a stray "ACCEPT:" prefix from the critic are removed.
- Emails and phone numbers are redacted (web pages sometimes contain them).
- Reports with no citations, or very short ones, are flagged, not blocked: the
  user still sees them, with a warning.
"""
import re

from app.guardrails import event

# 1-2 digits only, so years like [2024] aren't mistaken for citations
CITATION_RE = re.compile(r"\[(\d{1,2}(?:\s*,\s*\d{1,2})*)\]")
_LEAKED_PREFIX_RE = re.compile(r"^\s*(ACCEPT|REJECT)\s*:\s*", re.IGNORECASE)
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PHONE_RE = re.compile(r"(?<!\w)\+?\d{1,3}[\s.-]?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b")

MIN_REPORT_WORDS = 80


def find_citations(text: str) -> list[int]:
    return [int(n) for group in CITATION_RE.findall(text or "") for n in group.split(",")]


def strip_invalid_citations(report: str, num_sources: int) -> tuple[str, list[int]]:
    removed = []

    def keep_valid(match):
        numbers = [int(n) for n in match.group(1).split(",")]
        valid = [n for n in numbers if 1 <= n <= num_sources]
        removed.extend(n for n in numbers if n not in valid)
        return f"[{', '.join(map(str, valid))}]" if valid else ""

    return CITATION_RE.sub(keep_valid, report), removed


def enforce_report(report: str, num_sources: int) -> tuple[str, list[dict]]:
    events = []

    if _LEAKED_PREFIX_RE.match(report):
        report = _LEAKED_PREFIX_RE.sub("", report, count=1)
        events.append(event("output.protocol_leak", "removed", "critic prefix in final report"))

    report, removed = strip_invalid_citations(report, num_sources)
    if removed:
        events.append(event(
            "output.invalid_citations", "removed",
            f"{sorted(set(removed))} (only {num_sources} sources exist)",
        ))

    report, emails = _EMAIL_RE.subn("[redacted email]", report)
    report, phones = _PHONE_RE.subn("[redacted phone]", report)
    if emails or phones:
        events.append(event("output.pii", "redacted", f"{emails} email(s), {phones} phone number(s)"))

    if not find_citations(report):
        events.append(event("output.no_citations", "flagged", "report makes no cited claims"))
    if len(report.split()) < MIN_REPORT_WORDS:
        events.append(event("output.too_short", "flagged", f"{len(report.split())} words"))

    return report.strip(), events
