"""Integration tests for FastAPI endpoints."""

import pytest
from fastapi.testclient import TestClient
from sketchflow.main import app
from sketchflow.schemas.diagram import SketchNode, SketchEdge, SketchGraph

client = TestClient(app)

def test_root_endpoint():
    """Verify root endpoint serves the SketchFlow web UI or redirects to Swagger UI."""
    response = client.get("/", follow_redirects=False)
    if response.status_code == 200:
        assert "SketchFlow" in response.text
    else:
        assert response.status_code in [307, 302]
        assert response.headers["location"] == "/docs"


def test_health_endpoint():
    """Verify health endpoint returns status and provider configuration."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "SketchFlow"
    assert "providers" in data

def test_workflows_compile_endpoint():
    """Verify workflows compile endpoint transforms a SketchGraph into n8n JSON."""
    payload = {
        "graph": {
            "nodes": [
                {"id": "n1", "label": "Start Webhook", "kind": "trigger", "shape": "rectangle"},
                {"id": "n2", "label": "Send Notification", "kind": "action", "shape": "rectangle"}
            ],
            "edges": [
                {"from_id": "n1", "to_id": "n2", "label": None}
            ],
            "ambiguities": []
        },
        "workflow_name": "API Test Workflow"
    }
    response = client.post("/api/v1/workflows/compile", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["node_count"] == 2
    assert data["workflow"]["name"] == "API Test Workflow"
    assert len(data["workflow"]["nodes"]) == 2
    assert "Start Webhook" in data["workflow"]["connections"]

def test_diagram_extract_invalid_payload():
    """Verify extract endpoint validates request schema."""
    response = client.post("/api/v1/diagrams/extract", json={})
    assert response.status_code == 422

def test_agent_run_and_resume_sse_streaming():
    """Verify agent SSE streaming emits structured events for both run and resume."""
    from unittest.mock import patch
    from sketchflow.schemas.diagram import DiagramExtractResponse
    from sketchflow.schemas.workflow import N8nWorkflowDTO, CompileWorkflowResponse
    from sketchflow.schemas.deployment import DeployWorkflowResponse, TestWebhookResponse

    mock_extract = DiagramExtractResponse(
        graph=SketchGraph(nodes=[SketchNode(id="n1", label="Webhook", kind="trigger")], edges=[]),
        model_used="test-model",
        provider_used="nvidia",
        latency_seconds=0.3,
        total_nodes=1,
        total_edges=0
    )
    mock_compile = CompileWorkflowResponse(
        workflow=N8nWorkflowDTO(name="Stream Test WF", nodes=[], connections={}),
        layout_positions={"n1": [250, 300]},
        validation_report={"valid": True, "errors": []},
        node_count=1,
        connection_count=0
    )
    mock_deploy = DeployWorkflowResponse(
        success=True,
        workflow_id="wf_stream_test",
        workflow_name="Stream Test WF",
        active=True,
        webhook_urls=["http://localhost:5678/webhook/test"],
        editor_url="http://localhost:5678/workflow/wf_stream_test",
        message="Deployed successfully"
    )
    mock_test_hook = TestWebhookResponse(
        success=True,
        webhook_url="http://localhost:5678/webhook/test",
        status_code=200,
        response_data={"status": "ok"},
        latency_ms=30.0,
        message="Webhook fired successfully"
    )

    thread_id = "test-sse-thread"
    with patch("sketchflow.agent.nodes.vision_service.extract_from_file", return_value=mock_extract), \
         patch("sketchflow.agent.nodes.compiler_service.compile", return_value=mock_compile), \
         patch("sketchflow.agent.nodes.n8n_service.deploy_workflow", return_value=mock_deploy), \
         patch("sketchflow.agent.nodes.n8n_service.test_webhook", return_value=mock_test_hook):

        # 1. Run SSE stream to checkpoint
        run_res = client.post("/api/v1/agent/run-stream", json={"image_path": "dummy.jpg", "thread_id": thread_id})
        assert run_res.status_code == 200
        assert "text/event-stream" in run_res.headers.get("content-type", "")
        run_text = run_res.text
        assert "event: started" in run_text
        assert "event: node_update" in run_text
        assert "event: checkpoint" in run_text
        assert "event: done" in run_text

        # 2. Resume SSE stream to completion
        resume_res = client.post("/api/v1/agent/resume-stream", json={"thread_id": thread_id, "human_approved": True})
        assert resume_res.status_code == 200
        assert "text/event-stream" in resume_res.headers.get("content-type", "")
        resume_text = resume_res.text
        assert "event: resumed" in resume_text
        assert "event: complete" in resume_text
        assert "event: done" in resume_text

