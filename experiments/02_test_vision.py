"""
Experiment 02: Vision Perception via Multimodal VLM & Strongly-Typed Schema
- Primary: 'moonshotai/kimi-k3' via NVIDIA NIM (High-fidelity Multimodal)
- Fallback: 'qwen/qwen3.8-27b' via Groq Cloud (Ultra-fast JSON Vision)
Extracts a strongly-typed Pydantic SketchGraph directly from the sketch image.
"""

import os
import sys
import json
import base64
import time
import re
from typing import List, Optional, Literal

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from pydantic import BaseModel, Field

class SketchNode(BaseModel):
    id: str = Field(description="Unique node identifier, e.g. 'node_1'")
    label: str = Field(description="Exact handwritten text inside the shape")
    kind: Literal["trigger", "condition", "action", "unknown"] = Field(
        description="Trigger (start), Condition (decision/diamond), Action (process), or Unknown"
    )
    shape: Optional[str] = Field(default="rectangle", description="Shape type (rectangle, diamond, circle)")

class SketchEdge(BaseModel):
    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    label: Optional[str] = Field(default=None, description="Branch label, e.g. 'yes', 'no', 'true', 'false'")

class SketchGraph(BaseModel):
    nodes: List[SketchNode] = Field(description="All detected diagram shapes and text")
    edges: List[SketchEdge] = Field(description="All directed arrows connecting shapes")
    ambiguities: List[str] = Field(default_factory=list, description="Any unclear handwriting or layout notes")

def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def clean_json_output(raw_text: str) -> str:
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text

def test_langchain_vision(image_path="experiments/sample_sketch.jpg"):
    if not os.path.exists(image_path):
        print(f"❌ Image file {image_path} not found.")
        return None

    try:
        from langchain_core.messages import HumanMessage
        from langchain.chat_models import init_chat_model
    except ImportError:
        print("⚠️ LangChain is not installed in current environment.")
        return None

    base64_img = encode_image(image_path)
    data_uri = f"data:image/jpeg;base64,{base64_img}"
    
    schema_str = json.dumps(SketchGraph.model_json_schema(), indent=2)
    prompt_content = f"""You are an expert visual diagram parser.
Analyze this hand-drawn flowchart sketch and identify every node (box, diamond, trigger) and every directed arrow connection.

Return ONLY a valid JSON object matching this JSON schema:
{schema_str}
"""

    message = HumanMessage(content=[
        {"type": "text", "text": prompt_content},
        {"type": "image_url", "image_url": {"url": data_uri}}
    ])

    # 1. Primary: NVIDIA NIM (moonshotai/kimi-k3)
    if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("your_"):
        print(f"\n[LangChain Vision] Testing NVIDIA NIM (moonshotai/kimi-k3) with: {image_path}...")
        try:
            llm = init_chat_model(
                model="moonshotai/kimi-k3",
                model_provider="nvidia",
                api_key=NVIDIA_API_KEY,
                temperature=0.1
            )
            start = time.perf_counter()
            response = llm.invoke([message])
            elapsed = time.perf_counter() - start

            cleaned = clean_json_output(response.content)
            result = SketchGraph.model_validate_json(cleaned)
            print(f"✅ NVIDIA NIM (kimi-k3) Vision Succeeded ({elapsed:.2f}s)!")
            print(f"Nodes found: {len(result.nodes)}, Edges: {len(result.edges)}")
            print(result.model_dump_json(indent=2))
            return result
        except Exception as e:
            print(f"⚠️ NVIDIA Vision failed: {e}. Trying Groq fallback...")

    # 2. Fallback: Groq Cloud (qwen/qwen3.8-27b)
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"):
        print(f"\n[LangChain Vision] Testing Groq Cloud (qwen/qwen3.8-27b) with: {image_path}...")
        try:
            llm = init_chat_model(
                model="qwen/qwen3.8-27b",
                model_provider="groq",
                api_key=GROQ_API_KEY,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            start = time.perf_counter()
            response = llm.invoke([message])
            elapsed = time.perf_counter() - start

            cleaned = clean_json_output(response.content)
            result = SketchGraph.model_validate_json(cleaned)
            print(f"✅ Groq Vision Succeeded ({elapsed:.2f}s)!")
            print(f"Nodes found: {len(result.nodes)}, Edges: {len(result.edges)}")
            print(result.model_dump_json(indent=2))
            return result
        except Exception as e:
            print(f"❌ Groq Vision failed: {e}")

    print("⚠️ No valid responses received from configured vision providers.")
    return None

if __name__ == "__main__":
    sketch_path = "experiments/sample_sketch.jpg"
    test_langchain_vision(sketch_path)
