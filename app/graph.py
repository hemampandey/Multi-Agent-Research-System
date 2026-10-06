import operator
from typing import Annotated, List, TypedDict

from langgraph.graph import END, StateGraph

from app import config
from app.agents.critic import review_report
from app.agents.planner import create_plan
from app.agents.writer import generate_report
from app.guardrails import GuardrailViolation, event
from app.guardrails.classifier import classify_topic
from app.guardrails.content import is_allowed_url, sanitize_source_text
from app.guardrails.input import validate_mode, validate_topic
from app.guardrails.output import enforce_report, find_citations
from app.harness.tracing import traced
from app.tools.search import search_web


class GraphState(TypedDict, total=False):
    topic: str
    mode: str
    questions: List[str]
    data: str
    report: str
    final_report: str
    raw_report: str  # final report before output guardrails (evals measure both)
    sources: List[str]
    critic_feedback: str
    revision_count: int
    # Every node can append; the reducer concatenates instead of overwriting
    guardrail_events: Annotated[List[dict], operator.add]


def input_guard_node(state: GraphState):
    topic = validate_topic(state.get("topic"))  # layer 1: free regex checks
    mode = validate_mode(state.get("mode"))
    events = classify_topic(topic)              # layer 2: LLM checks the intent
    return {
        "topic": topic,
        "mode": mode,
        "revision_count": 0,
        "critic_feedback": "",
        "guardrail_events": events,
    }


def planner_node(state: GraphState):
    if state["mode"] == "Basic":
        return {"questions": [state["topic"]]}

    questions = create_plan(state["topic"])[:config.MAX_QUESTIONS]
    if not questions:
        return {
            "questions": [state["topic"]],
            "guardrail_events": [event("planner.unparseable", "fallback", "researching the topic directly")],
        }
    return {"questions": questions}


def research_node(state: GraphState):
    # Each *source* gets its own number, in order, so that [n] in the report
    # always means sources[n - 1].
    sources, blocks, events = [], [], []

    for question in state["questions"]:
        for result in search_web(question + " explanation examples").get("results", []):
            url = result.get("url", "")
            content = result.get("content") or result.get("snippet") or ""
            if not is_allowed_url(url) or url in sources or not content.strip():
                continue

            text, flags = sanitize_source_text(content)
            events += [event(f"content.{flag}", "sanitized", url) for flag in flags]

            sources.append(url)
            blocks.append(f"[{len(sources)}] {result.get('title', '')} ({url})\n{text}")

    if not sources:
        raise GuardrailViolation(
            "no_sources",
            "Web search returned no usable sources, so there is nothing to ground a report on.",
        )

    return {"data": "\n\n".join(blocks), "sources": sources, "guardrail_events": events}


def writer_node(state: GraphState):
    report = generate_report(
        state["topic"],
        state["data"],
        previous_report=state.get("report", ""),
        feedback=state.get("critic_feedback", ""),
    )
    return {"report": report}


def critic_node(state: GraphState):
    draft = state["report"]
    review = review_report(draft, state["topic"]).strip()

    if review.startswith("REJECT:"):
        return {
            "final_report": draft,
            "critic_feedback": review.removeprefix("REJECT:").strip(),
            "revision_count": state.get("revision_count", 0) + 1,
        }

    if review.startswith("ACCEPT:"):
        polished = review.removeprefix("ACCEPT:").strip()
        # The critic may polish wording, but not un-ground the report
        if not polished or (find_citations(draft) and not find_citations(polished)):
            return {
                "final_report": draft,
                "critic_feedback": "accept",
                "guardrail_events": [event("critic.dropped_citations", "kept_draft",
                                           "polished version lost its citations")],
            }
        return {"final_report": polished, "critic_feedback": "accept"}

    # The critic ignored the ACCEPT/REJECT protocol: don't trust its text as a report
    return {
        "final_report": draft,
        "critic_feedback": "accept",
        "guardrail_events": [event("critic.unparseable", "kept_draft", review[:120])],
    }


def output_guard_node(state: GraphState):
    report, events = enforce_report(state["final_report"], len(state["sources"]))
    return {"raw_report": state["final_report"], "final_report": report, "guardrail_events": events}


def should_continue(state: GraphState):
    if state.get("critic_feedback") == "accept" or state.get("revision_count", 0) >= config.MAX_REVISIONS:
        return "finalize"
    return "writer"


builder = StateGraph(GraphState)

builder.add_node("input_guard", traced("input_guard")(input_guard_node))
builder.add_node("planner", traced("planner")(planner_node))
builder.add_node("research", traced("research")(research_node))
builder.add_node("writer", traced("writer")(writer_node))
builder.add_node("critic", traced("critic")(critic_node))
builder.add_node("output_guard", traced("output_guard")(output_guard_node))

builder.set_entry_point("input_guard")

builder.add_edge("input_guard", "planner")
builder.add_edge("planner", "research")
builder.add_edge("research", "writer")
builder.add_edge("writer", "critic")

# Self-correction loop: the critic either sends the draft back or lets it through
builder.add_conditional_edges(
    "critic",
    should_continue,
    {
        "writer": "writer",
        "finalize": "output_guard",
    }
)
builder.add_edge("output_guard", END)

graph = builder.compile()
