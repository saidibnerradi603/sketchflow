"""Endpoints for flowchart image diagram perception."""

import base64
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from typing import Optional
from sketchflow.schemas.diagram import (
    DiagramExtractRequest,
    DiagramExtractResponse
)
from sketchflow.api.v1.deps import get_vision_service
from sketchflow.services.vision_service import VisionService

router = APIRouter()

@router.post("/extract", response_model=DiagramExtractResponse, summary="Extract diagram from base64 image")
async def extract_diagram_base64(
    request: DiagramExtractRequest,
    vision_service: VisionService = Depends(get_vision_service)
) -> DiagramExtractResponse:
    """Extracts a structured graph from a base64 encoded image string."""
    try:
        return vision_service.extract_from_base64(
            image_base64=request.image_base64,
            mime_type=request.mime_type,
            preferred_provider=request.preferred_provider
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload", response_model=DiagramExtractResponse, summary="Extract diagram from uploaded image file")
async def extract_diagram_upload(
    file: UploadFile = File(...),
    preferred_provider: Optional[str] = Form(default=None),
    vision_service: VisionService = Depends(get_vision_service)
) -> DiagramExtractResponse:
    """Extracts a structured graph directly from an uploaded image file."""
    try:
        content = await file.read()
        b64_str = base64.b64encode(content).decode("utf-8")
        mime = file.content_type or "image/jpeg"
        return vision_service.extract_from_base64(
            image_base64=b64_str,
            mime_type=mime,
            preferred_provider=preferred_provider
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
