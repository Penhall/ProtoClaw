from langgraph.graph import StateGraph, END

from protoclaw.orchestrator.nodes.decompose import decompose_node
from protoclaw.orchestrator.nodes.deploy import deploy_node
from protoclaw.orchestrator.nodes.generate_nanobot import generate_nanobot_node
from protoclaw.orchestrator.nodes.generate_openclaw import generate_openclaw_node
from protoclaw.orchestrator.nodes.guardrails import guardrails_node
from protoclaw.orchestrator.nodes.parse import parse_node
from protoclaw.orchestrator.nodes.report import report_node
from protoclaw.orchestrator.nodes.select import select_node
from protoclaw.orchestrator.state import ProtoclawState


def _route_after_select(state: ProtoclawState) -> str:
    if state.get("error"):
        return END
    return f"generate_{state['framework']}"


def build_graph():
    """Build and compile the ProtoClaw LangGraph pipeline."""
    workflow = StateGraph(ProtoclawState)

    workflow.add_node("parse", parse_node)
    workflow.add_node("decompose", decompose_node)
    workflow.add_node("guardrails", guardrails_node)
    workflow.add_node("select", select_node)
    workflow.add_node("generate_openclaw", generate_openclaw_node)
    workflow.add_node("generate_nanobot", generate_nanobot_node)
    workflow.add_node("deploy", deploy_node)
    workflow.add_node("report", report_node)

    workflow.set_entry_point("parse")
    workflow.add_edge("parse", "decompose")
    workflow.add_edge("decompose", "guardrails")
    workflow.add_edge("guardrails", "select")
    workflow.add_conditional_edges(
        "select",
        _route_after_select,
        {
            "generate_openclaw": "generate_openclaw",
            "generate_nanobot": "generate_nanobot",
            END: END,
        },
    )
    workflow.add_edge("generate_openclaw", "deploy")
    workflow.add_edge("generate_nanobot", "deploy")
    workflow.add_edge("deploy", "report")
    workflow.add_edge("report", END)

    return workflow.compile()
