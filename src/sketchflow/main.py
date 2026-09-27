"""
Main FastAPI Application Entrypoint.
Provides REST and WebSocket endpoints for SketchFlow.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from sketchflow.core.config import settings
from sketchflow.api.v1.router import api_router

from pathlib import Path
from fastapi.staticfiles import StaticFiles

UI_DIST_DIR = Path(__file__).parent / "ui" / "dist"

def create_application() -> FastAPI:
    """Application factory for SketchFlow API."""
    app = FastAPI(
        title=f"{settings.PROJECT_NAME} API",
        description="Autonomous diagram-to-n8n workflow automation engine.",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # Enable Cross-Origin Resource Sharing (CORS) for UI integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount API v1 router
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    # Mount UI static frontend if built, otherwise redirect to Swagger
    if UI_DIST_DIR.exists():
        app.mount("/", StaticFiles(directory=str(UI_DIST_DIR), html=True), name="static_ui")
    else:
        @app.get("/", include_in_schema=False)
        async def root_redirect():
            """Redirect root requests directly to Swagger UI."""
            return RedirectResponse(url="/docs")

    return app

app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("sketchflow.main:app", host="0.0.0.0", port=8000, reload=True)
