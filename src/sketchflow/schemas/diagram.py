"""
Diagram Schemas (DTOs) for visual sketch perception.
Generic and universal representation of nodes and connections in any diagram.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field

class SketchNode(BaseModel):
    """Represents any detected shape, box, or step in a diagram."""
    id: str = Field(description="Unique identifier for the node, e.g. 'node_1'")
    label: str = Field(description="Handwritten text or description detected inside the node")
    kind: Literal["trigger", "condition", "action", "unknown"] = Field(
        default="unknown",
        description="Functional role: trigger (event/start), condition (branch/decision), action (step), or unknown"
    )
    shape: Optional[str] = Field(
        default="rectangle",
        description="Visual shape type: 'rectangle', 'diamond', 'circle', 'pill', etc."
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional metadata such as bounding box, confidence, or notes"
    )

class SketchEdge(BaseModel):
    """Represents any directed connection or arrow between two nodes."""
    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    label: Optional[str] = Field(
        default=None,
        description="Condition or branch label on the arrow, e.g. 'yes', 'no', 'true', 'false', 'on error'"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Optional edge metadata"
    )

class SketchGraph(BaseModel):
    """Complete structured representation of an extracted diagram."""
    nodes: List[SketchNode] = Field(
        default_factory=list,
        description="All shapes and nodes extracted from the image"
    )
    edges: List[SketchEdge] = Field(
        default_factory=list,
        description="All directed connections between nodes"
    )
    ambiguities: List[str] = Field(
        default_factory=list,
        description="Any handwriting uncertainties, unclear arrows, or notes for user clarification"
    )

class DiagramExtractRequest(BaseModel):
    """Request payload for extracting a diagram from an encoded image."""
    image_base64: str = Field(description="Base64-encoded image string")
    mime_type: str = Field(default="image/jpeg", description="MIME type of the image")
    preferred_provider: Optional[Literal["nvidia", "groq"]] = Field(
        default=None,
        description="Optional provider override"
    )

class DiagramExtractResponse(BaseModel):
    """Response payload containing the parsed diagram graph."""
    graph: SketchGraph
    provider_used: str
    model_used: str
    latency_seconds: float
    total_nodes: int
    total_edges: int
