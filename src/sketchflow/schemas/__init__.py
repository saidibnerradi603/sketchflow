"""Pydantic Schemas (DTOs) for SketchFlow."""

from sketchflow.schemas.diagram import (
    SketchNode,
    SketchEdge,
    SketchGraph,
    DiagramExtractRequest,
    DiagramExtractResponse,
)

from sketchflow.schemas.workflow import (
    N8nNodeDTO,
    N8nConnectionItemDTO,
    N8nWorkflowDTO,
    CompileWorkflowRequest,
    CompileWorkflowResponse,
)

from sketchflow.schemas.deployment import (
    DeployWorkflowRequest,
    DeployWorkflowResponse,
    TestWebhookRequest,
    TestWebhookResponse,
    WorkflowStatusResponse,
)

__all__ = [
    "SketchNode",
    "SketchEdge",
    "SketchGraph",
    "DiagramExtractRequest",
    "DiagramExtractResponse",
    "N8nNodeDTO",
    "N8nConnectionItemDTO",
    "N8nWorkflowDTO",
    "CompileWorkflowRequest",
    "CompileWorkflowResponse",
    "DeployWorkflowRequest",
    "DeployWorkflowResponse",
    "TestWebhookRequest",
    "TestWebhookResponse",
    "WorkflowStatusResponse",
]
