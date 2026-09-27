"""API v1 Router aggregation."""

from fastapi import APIRouter
from sketchflow.api.v1.endpoints import (
    health,
    diagrams,
    workflows,
    deploy,
    agent
)

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health & Liveness"])
api_router.include_router(diagrams.router, prefix="/diagrams", tags=["Diagram Perception"])
api_router.include_router(workflows.router, prefix="/workflows", tags=["Workflow Compilation"])
api_router.include_router(deploy.router, prefix="/deploy", tags=["n8n Deployment & Verification"])
api_router.include_router(agent.router, prefix="/agent", tags=["Autonomous Agent Orchestrator"])
