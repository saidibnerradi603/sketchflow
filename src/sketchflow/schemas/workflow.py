"""
Workflow Schemas (DTOs) for compiling diagrams into authoritative n8n JSON.
Completely generic and compliant with n8n workflow specifications.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from sketchflow.schemas.diagram import SketchGraph

class N8nNodeDTO(BaseModel):
    """Authoritative representation of a single node in an n8n workflow."""
    id: str = Field(description="Unique node UUID within the workflow")
    name: str = Field(description="Display name of the node in the n8n canvas")
    type: str = Field(description="Full n8n node type string, e.g. 'n8n-nodes-base.webhook'")
    typeVersion: float = Field(default=1.0, description="Version of the n8n node specification")
    position: List[int] = Field(description="Canvas coordinates [x, y]")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Dynamic parameters dictionary required by this specific node type"
    )
    credentials: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional credential bindings reference"
    )

class N8nConnectionItemDTO(BaseModel):
    """Single connection target in n8n's connection matrix."""
    node: str = Field(description="Target node name")
    type: str = Field(default="main", description="Connection type, usually 'main'")
    index: int = Field(default=0, description="Target input index, usually 0")

class N8nWorkflowDTO(BaseModel):
    """Complete, valid n8n workflow JSON ready for deployment."""
    name: str = Field(description="Descriptive name of the automation workflow")
    nodes: List[N8nNodeDTO] = Field(description="List of all nodes in the workflow")
    connections: Dict[str, Dict[str, List[List[Dict[str, Any]]]]] = Field(
        default_factory=dict,
        description="n8n connection mapping dictionary with multi-output branching support"
    )
    settings: Dict[str, Any] = Field(
        default_factory=lambda: {"executionOrder": "v1"},
        description="Workflow runtime execution settings"
    )

class CompileWorkflowRequest(BaseModel):
    """Request payload to compile a SketchGraph into an n8n workflow."""
    graph: SketchGraph = Field(description="The source diagram graph")
    workflow_name: Optional[str] = Field(
        default=None,
        description="Optional custom workflow name; if omitted, AI generates one"
    )
    custom_parameters: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="Optional user-supplied parameter overrides keyed by node ID"
    )

class CompileWorkflowResponse(BaseModel):
    """Response payload containing compiled n8n workflow."""
    workflow: N8nWorkflowDTO
    node_count: int
    connection_count: int
    synthesizer_model: Optional[str] = None
    layout_calculated: bool = True
