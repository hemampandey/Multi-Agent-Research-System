from typing import TypedDict,List
from app.agents.critic import improve_report
from app.agents.planner import create_plan
from app.agents.writer import generate_report
from app.tools.search import search_web
from app.utils.helper import extract_content_and_source

class GraphState(TypedDict):
    topic: str
    mode: str
    questions: List[str]
    data: str
    report: str
    final_report: str
    sources: List[str]

def planner_node(state : GraphState):
    if state["mode"] == "Basic":
        return {"questions": [state["topic"]]}
    
    questions = create_plan(state["topic"])[:3]
    return {'questions' : questions}

def research_node(state : GraphState):
    all_data = ""
    all_sources = []

    for i,q in enumerate(state['questions'],1):
        results = search_web(q+" explanation examples")
        data,urls = extract_content_and_source(results)

        all_data += f"\n\n### [{i}]\n{data}"
        all_sources.extend(urls)

    return {
        "data" : all_data,
        "sources" : list(set(all_sources))  #remove duplicates
    }

def writer_node(state : GraphState):
    report = generate_report(state["topic"],state["data"])
    return{ "report" : report}

def critic_node(state : GraphState):
    final = improve_report(state["report"])
    return {"final_report": final}

from langgraph.graph import StateGraph

builder = StateGraph(GraphState)

builder.add_node("planner", planner_node)
builder.add_node("research", research_node)
builder.add_node("writer", writer_node)
builder.add_node("critic", critic_node)

builder.set_entry_point("planner")

builder.add_edge("planner", "research")
builder.add_edge("research", "writer")
builder.add_edge("writer", "critic")

graph = builder.compile()