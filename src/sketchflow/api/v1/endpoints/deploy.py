"""Endpoints for deploying workflows and firing test events to n8n."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sketchflow.schemas.deployment import (
    DeployWorkflowRequest,
    DeployWorkflowResponse,
    TestWebhookRequest,
    TestWebhookResponse,
    WorkflowStatusResponse
)
from sketchflow.api.v1.deps import get_n8n_service
from sketchflow.services.n8n_service import N8nService

router = APIRouter()

@router.get("/workflows", response_model=List[WorkflowStatusResponse], summary="List workflows in n8n")
async def list_workflows(
    limit: int = 10,
    n8n_service: N8nService = Depends(get_n8n_service)
) -> List[WorkflowStatusResponse]:
    """Retrieves existing workflows from the connected n8n instance."""
    try:
        return await n8n_service.list_workflows(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch workflows from n8n: {e}")

@router.post("/workflows", response_model=DeployWorkflowResponse, summary="Deploy and activate workflow in n8n")
async def deploy_workflow(
    request: DeployWorkflowRequest,
    n8n_service: N8nService = Depends(get_n8n_service)
) -> DeployWorkflowResponse:
    """Deploys the compiled n8n workflow JSON, activates it, and returns listening webhook URLs."""
    try:
        return await n8n_service.deploy_workflow(
            workflow=request.workflow,
            activate=request.activate
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"n8n deployment failed: {e}")

@router.post("/test-webhook", response_model=TestWebhookResponse, summary="Fire test event to active webhook")
async def test_webhook(
    request: TestWebhookRequest,
    n8n_service: N8nService = Depends(get_n8n_service)
) -> TestWebhookResponse:
    """Sends arbitrary test JSON into an active n8n webhook route and verifies response."""
    return await n8n_service.test_webhook(
        webhook_path=request.webhook_path,
        payload=request.payload,
        method=request.method
    )
