"""
LangGraph StateGraph compilation for SketchFlow.
Orchestrates autonomous diagram perception, compilation, human review checkpoint,
and deployment with self-healing feedback.

Uses SqliteSaver for persistent checkpointing (falls back to MemorySaver
if sqlite module is unavailable).
"""

from typing import Literal
from langgraph.graph import StateGraph, START, END

from sketchflow.agent.state import SketchFlowState
from sketchflow.agent.nodes import (
    perceive_node,
    compile_node,
    human_review_node,
    deploy_node,
    self_heal_node
)


def _create_checkpointer():
    """
    Creates the best available checkpointer.
    Prefers SqliteSaver for persistence; falls back to MemorySaver.
    """
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
        import sqlite3
        conn = sqlite3.connect(
            "sketchflow_checkpoints.db", check_same_thread=False
        )
        return SqliteSaver(conn)
    except (ImportError, Exception):
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()


def route_after_review(state: SketchFlowState) -> Literal["deploy", "__end__"]:
    """Determines whether to proceed to deployment or halt at the checkpoint."""
    if state.get("human_approved", False):
        return "deploy"
    return END


def route_after_deploy(state: SketchFlowState) -> Literal["self_heal", "__end__"]:
    """Routes to self-healing if execution issue occurred and retries remain."""
    if state.get("execution_error") and state.get("retry_count", 0) < 2:
        return "self_heal"
    return END


def create_sketchflow_graph(checkpointer: bool = True):
    """Builds and compiles the SketchFlow LangGraph StateGraph."""
    workflow = StateGraph(SketchFlowState)

    # Register graph nodes
    workflow.add_node("perceive", perceive_node)
    workflow.add_node("compile", compile_node)
    workflow.add_node("human_review", human_review_node)
    workflow.add_node("deploy", deploy_node)
    workflow.add_node("self_heal", self_heal_node)

    # Establish edges
    workflow.add_edge(START, "perceive")
    workflow.add_edge("perceive", "compile")
    workflow.add_edge("compile", "human_review")

    # Conditional branching
    workflow.add_conditional_edges(
        "human_review",
        route_after_review,
        {"deploy": "deploy", END: END}
    )

    workflow.add_conditional_edges(
        "deploy",
        route_after_deploy,
        {"self_heal": "self_heal", END: END}
    )

    workflow.add_edge("self_heal", "deploy")

    # Compile with persistent checkpointer and human-in-the-loop interruption
    memory = _create_checkpointer() if checkpointer else None
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["deploy"]
    )


# Singleton compiled agent graph instance
agent_graph = create_sketchflow_graph()
