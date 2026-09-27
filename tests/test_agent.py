"""Unit tests for the SketchFlow LangGraph Agent."""

import pytest
from sketchflow.agent.tools import (
    inspect_node_schema,
    calculate_dag_layout,
    validate_n8n_workflow
)
from sketchflow.agent.graph import create_sketchflow_graph
from sketchflow.schemas.diagram import SketchNode, SketchEdge, SketchGraph

def test_inspect_node_schema_tool():
    """Verify tool resolves known and custom node intents."""
    res_webhook = inspect_node_schema("lead intake webhook")
    assert res_webhook["found"] is True
    assert res_webhook["n8n_type"] == "n8n-nodes-base.webhook"

    res_if = inspect_node_schema("is vip check?")
    assert res_if["found"] is True
    assert res_if["n8n_type"] == "n8n-nodes-base.if"

    res_custom = inspect_node_schema("alien widget xyz")
    assert res_custom["found"] is False
    assert res_custom["n8n_type"] == "n8n-nodes-base.httpRequest"

def test_calculate_dag_layout_tool():
    """Verify DAG layout tool computes coordinates for nodes."""
    nodes = [
        {"id": "n1", "label": "Start", "kind": "trigger"},
        {"id": "n2", "label": "Process", "kind": "action"}
    ]
    edges = [{"from_id": "n1", "to_id": "n2", "label": None}]
    positions = calculate_dag_layout(nodes, edges)
    assert "n1" in positions
    assert "n2" in positions
    assert positions["n1"][0] < positions["n2"][0]

def test_validate_n8n_workflow_tool():
    """Verify workflow linter detects missing triggers and duplicate names."""
    invalid_wf = {
        "nodes": [
            {"name": "Step 1", "type": "n8n-nodes-base.code"},
            {"name": "Step 1", "type": "n8n-nodes-base.slack"} # duplicate
        ],
        "connections": {}
    }
    report = validate_n8n_workflow(invalid_wf)
    assert report["valid"] is False
    assert any("Duplicate" in err for err in report["errors"])
    assert any("no trigger" in err for err in report["errors"])

    valid_wf = {
        "nodes": [
            {"name": "My Webhook", "type": "n8n-nodes-base.webhook"},
            {"name": "My Alert", "type": "n8n-nodes-base.slack"}
        ],
        "connections": {
            "My Webhook": {"main": [[{"node": "My Alert", "type": "main", "index": 0}]]}
        }
    }
    valid_report = validate_n8n_workflow(valid_wf)
    assert valid_report["valid"] is True
    assert len(valid_report["errors"]) == 0

def test_agent_graph_pauses_at_human_review_checkpoint():
    """Verify agent executes up to human review and pauses before deploy."""
    import asyncio
    async def _run():
        n1 = SketchNode(id="n1", label="Webhook In", kind="trigger")
        n2 = SketchNode(id="n2", label="Send Alert", kind="action")
        e1 = SketchEdge(from_id="n1", to_id="n2")
        sample_graph = SketchGraph(nodes=[n1, n2], edges=[e1])

        initial_state = {
            "image_base64": None,
            "image_path": None,
            "sketch_graph": sample_graph,
            "human_approved": False,
            "retry_count": 0,
            "current_step": "started",
            "logs": []
        }

        from sketchflow.agent.nodes import compile_node, human_review_node
        compiled_state = await compile_node(initial_state)
        assert compiled_state["current_step"] == "compiled"
        assert compiled_state["compiled_workflow"] is not None

        review_state = await human_review_node({**initial_state, **compiled_state})
        assert review_state["current_step"] == "awaiting_review"

    asyncio.run(_run())

def test_agent_records_reasoning_and_tool_calls():
    """Verify nodes populate detailed tool_calls and reasoning_trace for inspection."""
    import asyncio
    async def _run():
        n1 = SketchNode(id="n1", label="Webhook In", kind="trigger")
        n2 = SketchNode(id="n2", label="Filter Active", kind="condition")
        e1 = SketchEdge(from_id="n1", to_id="n2")
        sample_graph = SketchGraph(nodes=[n1, n2], edges=[e1])

        initial_state = {
            "sketch_graph": sample_graph,
            "human_approved": False,
            "retry_count": 0,
            "current_step": "started",
            "logs": [],
            "tool_calls": [],
            "reasoning_trace": []
        }

        from sketchflow.agent.nodes import compile_node
        compiled_state = await compile_node(initial_state)
        assert len(compiled_state["tool_calls"]) >= 3
        tool_names = [tc["tool"] for tc in compiled_state["tool_calls"]]
        assert "inspect_node_schema" in tool_names
        assert "calculate_dag_layout" in tool_names
        assert "validate_n8n_workflow" in tool_names

        assert len(compiled_state["reasoning_trace"]) >= 1
        assert "compilation" in [r["step"] for r in compiled_state["reasoning_trace"]]

    asyncio.run(_run())


def test_search_n8n_docs_tool():
    """Verify search_n8n_docs returns documentation or expression reference."""
    import asyncio
    from sketchflow.agent.tools import search_n8n_docs

    async def _test():
        res_exp = await search_n8n_docs("expression syntax")
        assert len(res_exp) > 50
        assert "expression" in res_exp.lower() or "$json" in res_exp.lower()

        res_hook = await search_n8n_docs("webhook trigger")
        assert len(res_hook) > 50

    asyncio.run(_test())

