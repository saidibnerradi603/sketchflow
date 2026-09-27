"""Core application configuration and settings."""
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables and .env file.
    All keys are case-insensitive.
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # App Settings
    PROJECT_NAME: str = "SketchFlow"
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = False

    # AI Model Providers
    NVIDIA_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    DEFAULT_PROVIDER: str = "nvidia"

    # Multimodal Vision Model Configurations
    NVIDIA_VISION_MODEL: str = "moonshotai/kimi-k3"
    GROQ_VISION_MODEL: str = "qwen/qwen3.8-27b"

    # Workflow Architect / Compiler LLM Configurations
    NVIDIA_COMPILER_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b"
    GROQ_COMPILER_MODEL: str = "openai/gpt-oss-120b"

    # Self-Hosted n8n Instance Configuration
    N8N_BASE_URL: str = "http://localhost:5678/api/v1"
    N8N_API_KEY: Optional[str] = None
    N8N_WEBHOOK_BASE_URL: str = "http://localhost:5678/webhook"
    N8N_DOCKER_CONTAINER_NAME: str = "sketchflow_n8n"

# Singleton settings instance
settings = Settings()
