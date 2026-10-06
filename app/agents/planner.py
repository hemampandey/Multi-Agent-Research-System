import re

from app.llm import generate

_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")


def parse_questions(text):
    """Turn the model's list into clean questions, tolerating bullets/numbering."""
    questions = []
    for line in text.splitlines():
        question = _LIST_MARKER_RE.sub("", line).strip().strip("*").strip()
        if len(question) >= 5:
            questions.append(question)
    return questions


def create_plan(topic):
    prompt = f"""
    Break this topic into exactly 4 short research questions:

    Rules:
    - One line per question
    - No explanations
    - No headings
    - Only clean questions

    Topic: {topic}
    """

    return parse_questions(generate(prompt))
