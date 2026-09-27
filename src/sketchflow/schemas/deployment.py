"""
Deployment Schemas (DTOs) for deploying and testing workflows on an n8n instance.
Generic and decoupled from any specific third-party service.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
from sketchflow.schemas.workflow import N8nWorkflowDTO

class DeployWorkflowRequest(BaseModel):
    """Payload to deploy a compiled workflow to an n8n instance."""
    workflow: N8nWorkflowDTO = Field(description="The complete n8n workflow payload to deploy")
    activate: bool = Field(
        default=True,
        description="Whether to automatically publish/activate the workflow after creation"
    )

class DeployWorkflowResponse(BaseModel):
    """Result of a workflow deployment operation."""
    workflow_id: str = Field(description="The created n8n workflow ID")
    workflow_name: str = Field(description="Name of the workflow in n8n")
    active: bool = Field(description="Whether the workflow is active and listening for events")
    webhook_urls: List[str] = Field(
        default_factory=list,
        description="List of all exposed webhook endpoints for any trigger nodes in the workflow"
    )
    editor_url: str = Field(description="Direct URL to open and view the workflow in n8n UI")
    message: str = Field(default="Workflow deployed successfully")

class TestWebhookRequest(BaseModel):
    """Payload to fire an arbitrary test event to an active webhook."""
    __test__ = False
    webhook_path: Optional[str] = Field(default=None, description="The webhook route path or slug, e.g. 'lead-intake'")
    webhook_url: Optional[str] = Field(default=None, description="Full webhook URL (auto-extracts path slug if provided)")
    payload: Dict[str, Any] = Field(
        default_factory=dict,
        description="Any arbitrary JSON body to send into the webhook"
    )
    method: str = Field(default="POST", description="HTTP method to use (POST, GET, etc.)")

    @model_validator(mode="after")
    def resolve_path(self):
        if not self.webhook_path and self.webhook_url:
            self.webhook_path = self.webhook_url.split("/")[-1]
        if not self.webhook_path:
            self.webhook_path = "test"
        return self

class TestWebhookResponse(BaseModel):
    """Result of testing an active webhook trigger."""
    __test__ = False
    webhook_url: str = Field(description="The target URL that was called")
    status_code: int = Field(description="HTTP status code returned by n8n")
    success: bool = Field(description="True if request succeeded (HTTP 2xx)")
    response_data: Any = Field(description="Response body received from the webhook trigger")
    execution_id: Optional[str] = Field(
        default=None,
        description="n8n execution ID associated with this trigger, if available"
    )

class WorkflowStatusResponse(BaseModel):
    """Summary of a workflow's current operational state in n8n."""
    workflow_id: str
    name: str
    active: bool
    nodes_count: int
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
