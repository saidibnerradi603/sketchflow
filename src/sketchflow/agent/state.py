"""
State definition for the SketchFlow LangGraph StateGraph.
Tracks data through perception, compilation, human review, deployment, and repair.
"""

from typing import TypedDict, Optional, Dict, Any, List
from sketchflow.schemas.diagram import SketchGraph
from sketchflow.schemas.workflow import N8nWorkflowDTO
from sketchflow.schemas.deployment import (
    DeployWorkflowResponse,
    TestWebhookResponse
)

class SketchFlowState(TypedDict):
    """The central state of the autonomous SketchFlow pipeline."""

    # Input Data
    image_base64: Optional[str]
    image_path: Optional[str]
    preferred_provider: Optional[str]

    # Diagram Perception Step
    sketch_graph: Optional[SketchGraph]
    perception_model: Optional[str]
    perception_latency: Optional[float]

    # Compilation & Layout Step
    workflow_name: Optional[str]
    custom_parameters: Optional[Dict[str, Dict[str, Any]]]
    compiled_workflow: Optional[N8nWorkflowDTO]
    layout_positions: Optional[Dict[str, List[int]]]
    validation_report: Optional[Dict[str, Any]]

    # Human-in-the-Loop Checkpoint
    human_approved: bool
    user_feedback: Optional[str]

    # Deployment & Verification Step
    deployment_result: Optional[DeployWorkflowResponse]
    test_result: Optional[TestWebhookResponse]
    execution_error: Optional[str]

    # Control Flow & Telemetry
    retry_count: int
    current_step: str
    logs: List[str]
    tool_calls: List[Dict[str, Any]]
    reasoning_trace: List[Dict[str, Any]]
