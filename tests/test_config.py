"""Unit tests for core configuration settings."""
import os
import pytest
from sketchflow.core.config import Settings

def test_settings_defaults():
    settings = Settings(_env_file=None)
    assert settings.PROJECT_NAME == "SketchFlow"
    assert settings.API_V1_PREFIX == "/api/v1"
    assert settings.NVIDIA_VISION_MODEL == "moonshotai/kimi-k3"
    assert settings.GROQ_VISION_MODEL == "qwen/qwen3.8-27b"
    assert settings.NVIDIA_COMPILER_MODEL == "nvidia/nemotron-3-ultra-550b-a55b"
    assert settings.GROQ_COMPILER_MODEL == "openai/gpt-oss-120b"
    assert settings.N8N_BASE_URL == "http://localhost:5678/api/v1"

def test_settings_load_from_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "CustomSketchFlow")
    monkeypatch.setenv("DEFAULT_PROVIDER", "groq")
    settings = Settings(_env_file=None)
    assert settings.PROJECT_NAME == "CustomSketchFlow"
    assert settings.DEFAULT_PROVIDER == "groq"
