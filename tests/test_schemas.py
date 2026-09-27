"""Unit tests for universal DTO schemas."""
import json
import pytest
from pydantic import ValidationError
from sketchflow.schemas import (
    SketchNode,
    SketchEdge,
    SketchGraph,
    N8nNodeDTO,
    N8nWorkflowDTO,
    CompileWorkflowRequest,
    DeployWorkflowRequest,
    TestWebhookRequest,
    TestWebhookResponse
)

def test_sketch_graph_schema_generic():
    """Verify SketchGraph can represent arbitrary nodes and arrows."""
    node1 = SketchNode(
        id="node_stripe",
        label="Stripe Charge Succeeded",
        kind="trigger",
        shape="rectangle",
        metadata={"confidence": 0.98}
    )
    node2 = SketchNode(
        id="node_amount_check",
        label="Amount > $1000?",
        kind="condition",
        shape="diamond"
    )
    node3 = SketchNode(
        id="node_discord",
        label="Post to Discord VIP Channel",
        kind="action",
        shape="rectangle"
    )
    
    edge1 = SketchEdge(from_id="node_stripe", to_id="node_amount_check")
    edge2 = SketchEdge(from_id="node_amount_check", to_id="node_discord", label="True")

    graph = SketchGraph(nodes=[node1, node2, node3], edges=[edge1, edge2])
    
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 2
    assert graph.nodes[0].kind == "trigger"
    assert graph.nodes[1].shape == "diamond"
    assert graph.edges[1].label == "True"

    # Verify JSON serialization round-trip
    dumped = graph.model_dump_json()
    reloaded = SketchGraph.model_validate_json(dumped)
    assert reloaded == graph

def test_sketch_node_validation_error():
    """Verify invalid node kind raises ValidationError."""
    with pytest.raises(ValidationError):
        SketchNode(id="n1", label="Test", kind="invalid_kind")

def test_n8n_workflow_dto_generic():
    """Verify N8nWorkflowDTO supports arbitrary node types and dynamic parameters."""
    node = N8nNodeDTO(
        id="uuid-1234",
        name="Postgres Query",
        type="n8n-nodes-base.postgres",
        typeVersion=2.1,
        position=[300, 200],
        parameters={
            "operation": "executeQuery",
            "query": "SELECT * FROM users WHERE status = 'active';"
        }
    )
    
    workflow = N8nWorkflowDTO(
        name="Database Sync Pipeline",
        nodes=[node],
        connections={
            "Postgres Query": {
                "main": [[{"node": "Next Step", "type": "main", "index": 0}]]
            }
        },
        settings={"executionOrder": "v1"}
    )
    
    assert workflow.name == "Database Sync Pipeline"
    assert workflow.nodes[0].type == "n8n-nodes-base.postgres"
    assert workflow.nodes[0].parameters["operation"] == "executeQuery"
    assert "main" in workflow.connections["Postgres Query"]

def test_deployment_schemas_generic():
    """Verify deployment request and test webhook schemas with arbitrary JSON."""
    test_req = TestWebhookRequest(
        webhook_path="custom-intake",
        payload={
            "customer_id": "cust_998",
            "tier": "enterprise",
            "tags": ["urgent", "escalated"]
        },
        method="POST"
    )
    assert test_req.webhook_path == "custom-intake"
    assert test_req.payload["tier"] == "enterprise"

    # Test auto-extraction of path from webhook_url
    url_req = TestWebhookRequest(
        webhook_url="http://localhost:5678/webhook/auto-slug-test",
        payload={"foo": "bar"}
    )
    assert url_req.webhook_path == "auto-slug-test"

    test_res = TestWebhookResponse(
        webhook_url="http://localhost:5678/webhook/custom-intake",
        status_code=200,
        success=True,
        response_data={"message": "Workflow was started"},
        execution_id="exec_42"
    )
    assert test_res.success is True
    assert test_res.status_code == 200
    assert test_res.execution_id == "exec_42"
