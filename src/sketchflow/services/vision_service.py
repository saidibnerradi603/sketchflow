"""
Vision Service for diagram perception.
Extracts strongly-typed SketchGraph from flowchart images using multimodal VLMs.
- Primary: 'moonshotai/kimi-k3' via NVIDIA NIM
- Fallback: 'qwen/qwen3.8-27b' via Groq Cloud
"""

import os
import re
import json
import base64
import time
from typing import Optional, Tuple
from sketchflow.core.config import settings, Settings
from sketchflow.schemas.diagram import (
    SketchGraph,
    DiagramExtractResponse
)

class VisionService:
    """Service to process flowchart images and extract structured diagram graphs."""

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or settings

    def _clean_json_output(self, raw_text: str) -> str:
        """Strips markdown code blocks and whitespace from LLM response."""
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    def _build_prompt(self) -> str:
        """Constructs schema-enforced prompt for the multimodal model using the production ReAct protocol."""
        from sketchflow.agent.prompts import VISION_SYSTEM_PROMPT
        schema_str = json.dumps(SketchGraph.model_json_schema(), indent=2)
        return (
            f"{VISION_SYSTEM_PROMPT}\n\n"
            f"## Expected JSON Output Schema\n"
            f"{schema_str}"
        )

    def _call_nvidia(self, data_uri: str, prompt_text: str) -> Tuple[SketchGraph, float]:
        """Calls NVIDIA NIM with moonshotai/kimi-k3."""
        from langchain_core.messages import HumanMessage
        from langchain.chat_models import init_chat_model

        if not self.config.NVIDIA_API_KEY:
            raise ValueError("NVIDIA_API_KEY is not configured")

        llm = init_chat_model(
            model=self.config.NVIDIA_VISION_MODEL,
            model_provider="nvidia",
            api_key=self.config.NVIDIA_API_KEY,
            temperature=0.1
        )
        message = HumanMessage(content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": data_uri}}
        ])

        start = time.perf_counter()
        response = llm.invoke([message])
        elapsed = time.perf_counter() - start

        cleaned = self._clean_json_output(response.content)
        graph = SketchGraph.model_validate_json(cleaned)
        return graph, elapsed

    def _call_groq(self, data_uri: str, prompt_text: str) -> Tuple[SketchGraph, float]:
        """Calls Groq Cloud with qwen/qwen3.8-27b."""
        from langchain_core.messages import HumanMessage
        from langchain.chat_models import init_chat_model

        if not self.config.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not configured")

        llm = init_chat_model(
            model=self.config.GROQ_VISION_MODEL,
            model_provider="groq",
            api_key=self.config.GROQ_API_KEY,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        message = HumanMessage(content=[
            {"type": "text", "text": prompt_text},
            {"type": "image_url", "image_url": {"url": data_uri}}
        ])

        start = time.perf_counter()
        response = llm.invoke([message])
        elapsed = time.perf_counter() - start

        cleaned = self._clean_json_output(response.content)
        graph = SketchGraph.model_validate_json(cleaned)
        return graph, elapsed

    def extract_from_base64(
        self,
        image_base64: str,
        mime_type: str = "image/jpeg",
        preferred_provider: Optional[str] = None
    ) -> DiagramExtractResponse:
        """Extracts a SketchGraph from a base64 encoded image string."""
        raw_b64 = image_base64.strip()
        if raw_b64.startswith("data:"):
            data_uri = raw_b64
        else:
            data_uri = f"data:{mime_type};base64,{raw_b64}"

        prompt = self._build_prompt()

        provider = preferred_provider or self.config.DEFAULT_PROVIDER
        errors = []

        if provider == "groq":
            try:
                graph, elapsed = self._call_groq(data_uri, prompt)
                return DiagramExtractResponse(
                    graph=graph,
                    provider_used="groq",
                    model_used=self.config.GROQ_VISION_MODEL,
                    latency_seconds=round(elapsed, 3),
                    total_nodes=len(graph.nodes),
                    total_edges=len(graph.edges)
                )
            except Exception as e:
                errors.append(f"Groq failed: {e}")

        # Try NVIDIA NIM
        if self.config.NVIDIA_API_KEY:
            try:
                graph, elapsed = self._call_nvidia(data_uri, prompt)
                return DiagramExtractResponse(
                    graph=graph,
                    provider_used="nvidia",
                    model_used=self.config.NVIDIA_VISION_MODEL,
                    latency_seconds=round(elapsed, 3),
                    total_nodes=len(graph.nodes),
                    total_edges=len(graph.edges)
                )
            except Exception as e:
                errors.append(f"NVIDIA failed: {e}")

        # Fallback to Groq if not already attempted
        if provider != "groq" and self.config.GROQ_API_KEY:
            try:
                graph, elapsed = self._call_groq(data_uri, prompt)
                return DiagramExtractResponse(
                    graph=graph,
                    provider_used="groq",
                    model_used=self.config.GROQ_VISION_MODEL,
                    latency_seconds=round(elapsed, 3),
                    total_nodes=len(graph.nodes),
                    total_edges=len(graph.edges)
                )
            except Exception as e:
                errors.append(f"Groq fallback failed: {e}")

        raise RuntimeError(f"All vision providers failed: {'; '.join(errors)}")

    def extract_from_file(
        self,
        file_path: str,
        preferred_provider: Optional[str] = None
    ) -> DiagramExtractResponse:
        """Extracts diagram from a local file path."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")

        mime = "image/png" if file_path.lower().endswith(".png") else "image/jpeg"
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")

        return self.extract_from_base64(b64, mime_type=mime, preferred_provider=preferred_provider)
