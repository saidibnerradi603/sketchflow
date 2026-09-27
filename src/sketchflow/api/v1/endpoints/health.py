"""Health check endpoints for SketchFlow and n8n."""

from fastapi import APIRouter, Depends
from typing import Dict, Any
from sketchflow.api.v1.deps import get_n8n_service
from sketchflow.services.n8n_service import N8nService
from sketchflow.core.config import settings

router = APIRouter()

@router.get("", summary="System Health & Provider Status")
async def health_check(n8n_service: N8nService = Depends(get_n8n_service)) -> Dict[str, Any]:
    """Returns status of SketchFlow API, AI Providers, and local n8n instance."""
    n8n_healthy = await n8n_service.check_health()
    return {
        "status": "healthy",
        "app": settings.PROJECT_NAME,
        "n8n_connected": n8n_healthy,
        "n8n_base_url": settings.N8N_BASE_URL,
        "providers": {
            "nvidia_configured": bool(settings.NVIDIA_API_KEY),
            "groq_configured": bool(settings.GROQ_API_KEY),
            "default_provider": settings.DEFAULT_PROVIDER
        }
    }
