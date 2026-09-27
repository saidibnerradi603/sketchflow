"""Endpoints for compiling diagrams into authoritative n8n workflows."""

from fastapi import APIRouter, Depends, HTTPException
from sketchflow.schemas.workflow import (
    CompileWorkflowRequest,
    CompileWorkflowResponse
)
from sketchflow.api.v1.deps import get_compiler_service
from sketchflow.services.compiler_service import CompilerService

router = APIRouter()

@router.post("/compile", response_model=CompileWorkflowResponse, summary="Compile SketchGraph into n8n Workflow JSON")
async def compile_workflow(
    request: CompileWorkflowRequest,
    compiler_service: CompilerService = Depends(get_compiler_service)
) -> CompileWorkflowResponse:
    """
    Computes topological canvas coordinates, synthesizes parameters with LLM,
    and returns a production-ready n8n workflow payload.
    """
    try:
        return compiler_service.compile(
            graph=request.graph,
            workflow_name=request.workflow_name,
            custom_parameters=request.custom_parameters
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
