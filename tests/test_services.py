"""Unit tests for the Core Services layer."""
import pytest
from sketchflow.schemas.diagram import SketchNode, SketchEdge, SketchGraph
from sketchflow.services.compiler_service import CompilerService
from sketchflow.services.vision_service import VisionService
from sketchflow.services.n8n_service import N8nService
from sketchflow.core.config import Settings

def test_compiler_dag_layout_linear():
    """Verify linear DAG receives sequential X layers."""
    compiler = CompilerService(Settings(_env_file=None))
    n1 = SketchNode(id="n1", label="Start", kind="trigger")
    n2 = SketchNode(id="n2", label="Process", kind="action")
    n3 = SketchNode(id="n3", label="End", kind="action")
    e1 = SketchEdge(from_id="n1", to_id="n2")
    e2 = SketchEdge(from_id="n2", to_id="n3")
    graph = SketchGraph(nodes=[n1, n2, n3], edges=[e1, e2])

    positions = compiler.compute_dag_positions(graph)
    assert len(positions) == 3
    # X coordinates must strictly increase with depth
    assert positions["n1"][0] < positions["n2"][0]
    assert positions["n2"][0] < positions["n3"][0]

def test_compiler_dag_layout_branching():
    """Verify branching DAG places parallel branches on different Y coordinates."""
    compiler = CompilerService(Settings(_env_file=None))
    n1 = SketchNode(id="n1", label="Trigger", kind="trigger")
    n2 = SketchNode(id="n2", label="Check", kind="condition", shape="diamond")
    n3 = SketchNode(id="n3", label="Action A", kind="action")
    n4 = SketchNode(id="n4", label="Action B", kind="action")
    
    e1 = SketchEdge(from_id="n1", to_id="n2")
    e2 = SketchEdge(from_id="n2", to_id="n3", label="yes")
    e3 = SketchEdge(from_id="n2", to_id="n4", label="no")
    graph = SketchGraph(nodes=[n1, n2, n3, n4], edges=[e1, e2, e3])

    positions = compiler.compute_dag_positions(graph)
    assert len(positions) == 4
    # Action A and Action B share the same layer (same X) but different Y
    assert positions["n3"][0] == positions["n4"][0]
    assert positions["n3"][1] != positions["n4"][1]

def test_compiler_service_compilation_and_connections():
    """Verify compiler generates valid n8n connections with true/false branch indexing."""
    compiler = CompilerService(Settings(_env_file=None))
    n1 = SketchNode(id="n1", label="Webhook In", kind="trigger")
    n2 = SketchNode(id="n2", label="Is Active?", kind="condition")
    n3 = SketchNode(id="n3", label="Send Email", kind="action")
    n4 = SketchNode(id="n4", label="Archive", kind="action")
    
    e1 = SketchEdge(from_id="n1", to_id="n2")
    e2 = SketchEdge(from_id="n2", to_id="n3", label="True")
    e3 = SketchEdge(from_id="n2", to_id="n4", label="False")
    graph = SketchGraph(nodes=[n1, n2, n3, n4], edges=[e1, e2, e3])

    res = compiler.compile(
        graph,
        workflow_name="Test Branching Workflow",
        custom_parameters={"n1": {"path": "custom-route"}}
    )

    wf = res.workflow
    assert wf.name == "Test Branching Workflow"
    assert len(wf.nodes) == 4
    
    # Verify custom parameter override merged into Webhook node
    webhook_node = next(n for n in wf.nodes if n.name == "Webhook In")
    assert webhook_node.parameters["path"] == "custom-route"

    # Verify branching connections
    assert "Is Active?" in wf.connections
    branch_conn = wf.connections["Is Active?"]["main"]
    assert len(branch_conn) == 2
    # branch 0 (True) -> Send Email
    assert branch_conn[0][0]["node"] == "Send Email"
    # branch 1 (False) -> Archive
    assert branch_conn[1][0]["node"] == "Archive"

def test_vision_service_json_cleaner():
    """Verify markdown code block stripper handles various formats."""
    vs = VisionService(Settings(_env_file=None))
    
    raw1 = '```json\n{"nodes": []}\n```'
    assert vs._clean_json_output(raw1) == '{"nodes": []}'
    
    raw2 = '```\n{"nodes": []}\n```'
    assert vs._clean_json_output(raw2) == '{"nodes": []}'
    
    raw3 = '  {"nodes": []}  '
    assert vs._clean_json_output(raw3) == '{"nodes": []}'

def test_n8n_service_initialization():
    """Verify n8n service sets up base URLs and auth headers properly."""
    cfg = Settings(N8N_BASE_URL="http://test-host:5678/api/v1", N8N_API_KEY="test-key", _env_file=None)
    n8n = N8nService(cfg)
    assert n8n.base_url == "http://test-host:5678/api/v1"
    assert n8n.headers["X-N8N-API-KEY"] == "test-key"
