"""FastAPI Dependency Injection providers."""

from functools import lru_cache
from sketchflow.core.config import settings, Settings
from sketchflow.services.vision_service import VisionService
from sketchflow.services.compiler_service import CompilerService
from sketchflow.services.n8n_service import N8nService

@lru_cache()
def get_settings() -> Settings:
    """Provides application configuration settings."""
    return settings

def get_vision_service() -> VisionService:
    """Provides an instance of VisionService."""
    return VisionService(get_settings())

def get_compiler_service() -> CompilerService:
    """Provides an instance of CompilerService."""
    return CompilerService(get_settings())

def get_n8n_service() -> N8nService:
    """Provides an instance of N8nService."""
    return N8nService(get_settings())
