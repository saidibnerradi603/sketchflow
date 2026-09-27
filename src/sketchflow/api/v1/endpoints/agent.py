import json
import uuid
from typing import Optional, Dict, Any, List, AsyncGenerator
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from sketchflow.agent.graph import agent_graph
from sketchflow.schemas.diagram import SketchGraph
from sketchflow.schemas.workflow import N8nWorkflowDTO
from sketchflow.schemas.deployment import (
    DeployWorkflowResponse,
    TestWebhookResponse
)

router = APIRouter()

def serialize_for_sse(obj: Any) -> Any:
    """Recursively serializes objects including Pydantic models for SSE transmission."""
    if isinstance(obj, BaseModel):
        return obj.model_dump(exclude_none=True)
    if isinstance(obj, dict):
        return {k: serialize_for_sse(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [serialize_for_sse(v) for v in obj]
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return obj

def format_sse(event: str, data: Any) -> str:
    """Formats payload as a valid Server-Sent Events chunk."""
    serialized = serialize_for_sse(data)
    payload = json.dumps(serialized)
    return f"event: {event}\ndata: {payload}\n\n"

class StartAgentRequest(BaseModel):
    """Payload to initiate an autonomous workflow generation run."""
    image_base64: Optional[str] = Field(default=None, description="Base64 encoded image string")
    image_path: Optional[str] = Field(default=None, description="Local path to diagram image file")
    preferred_provider: Optional[str] = Field(default=None, description="Preferred vision provider (nvidia/groq)")
    thread_id: Optional[str] = Field(default=None, description="Optional thread identifier")

class ResumeAgentRequest(BaseModel):
    """Payload to approve checkpoint and resume execution towards deployment."""
    thread_id: str = Field(description="Active session thread ID paused at human review")
    human_approved: bool = Field(default=True, description="Approval flag from user")
    custom_parameters: Optional[Dict[str, Dict[str, Any]]] = Field(
        default=None,
        description="User-supplied credentials or parameters (e.g. Spreadsheet URL or Slack Channel)"
    )

class AgentStateResponse(BaseModel):
    """Response containing the current agent state and telemetry logs."""
    thread_id: str
    current_step: str
    sketch_graph: Optional[SketchGraph] = None
    compiled_workflow: Optional[N8nWorkflowDTO] = None
    layout_positions: Optional[Dict[str, List[int]]] = None
    validation_report: Optional[Dict[str, Any]] = None
    deployment_result: Optional[DeployWorkflowResponse] = None
    test_result: Optional[TestWebhookResponse] = None
    logs: List[str] = Field(default_factory=list)

@router.post("/run", response_model=AgentStateResponse, summary="Start Agent Pipeline to Human Review Checkpoint")
async def start_agent_pipeline(request: StartAgentRequest) -> AgentStateResponse:
    """
    Initiates diagram perception and compilation.
    Pauses at the human-in-the-loop review checkpoint for user inspection.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "image_base64": request.image_base64,
        "image_path": request.image_path,
        "preferred_provider": request.preferred_provider,
        "human_approved": False,
        "retry_count": 0,
        "current_step": "started",
        "logs": ["🚀 [Agent] Initializing autonomous SketchFlow pipeline..."]
    }

    try:
        final_state = await agent_graph.ainvoke(initial_state, config=config)
        return AgentStateResponse(
            thread_id=thread_id,
            current_step=final_state.get("current_step", "unknown"),
            sketch_graph=final_state.get("sketch_graph"),
            compiled_workflow=final_state.get("compiled_workflow"),
            layout_positions=final_state.get("layout_positions"),
            validation_report=final_state.get("validation_report"),
            logs=final_state.get("logs", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent execution failed: {e}")

@router.post("/resume", response_model=AgentStateResponse, summary="Resume Agent Pipeline After Human Approval")
async def resume_agent_pipeline(request: ResumeAgentRequest) -> AgentStateResponse:
    """
    Resumes an agent thread from the review checkpoint.
    Applies custom parameters (real Google Sheet URL, Slack channel) and deploys to n8n.
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    current_state = agent_graph.get_state(config)
    if not current_state or not current_state.values:
        raise HTTPException(status_code=404, detail=f"No active session found for thread_id '{request.thread_id}'")

    resume_patch = {
        "human_approved": request.human_approved
    }
    if request.custom_parameters:
        resume_patch["custom_parameters"] = request.custom_parameters

    try:
        # Update state with user approval and resume execution
        agent_graph.update_state(config, resume_patch)
        final_state = await agent_graph.ainvoke(None, config=config)

        return AgentStateResponse(
            thread_id=request.thread_id,
            current_step=final_state.get("current_step", "completed"),
            sketch_graph=final_state.get("sketch_graph"),
            compiled_workflow=final_state.get("compiled_workflow"),
            layout_positions=final_state.get("layout_positions"),
            validation_report=final_state.get("validation_report"),
            deployment_result=final_state.get("deployment_result"),
            test_result=final_state.get("test_result"),
            logs=final_state.get("logs", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to resume agent execution: {e}")

@router.get("/state/{thread_id}", response_model=AgentStateResponse, summary="Inspect Current Agent State")
async def get_agent_state(thread_id: str) -> AgentStateResponse:
    """Retrieves current telemetry and artifact states for an active thread."""
    config = {"configurable": {"thread_id": thread_id}}
    state_record = agent_graph.get_state(config)
    if not state_record or not state_record.values:
        raise HTTPException(status_code=404, detail=f"Thread '{thread_id}' not found.")

    v = state_record.values
    return AgentStateResponse(
        thread_id=thread_id,
        current_step=v.get("current_step", "unknown"),
        sketch_graph=v.get("sketch_graph"),
        compiled_workflow=v.get("compiled_workflow"),
        layout_positions=v.get("layout_positions"),
        validation_report=v.get("validation_report"),
        deployment_result=v.get("deployment_result"),
        test_result=v.get("test_result"),
        logs=v.get("logs", [])
    )

@router.post("/run-stream", summary="Stream Agent Pipeline Execution via SSE")
async def start_agent_pipeline_stream(request: StartAgentRequest):
    """
    Executes diagram perception and compilation with real-time SSE telemetry.
    Streams incremental updates and halts at the human review checkpoint.
    """
    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "image_base64": request.image_base64,
        "image_path": request.image_path,
        "preferred_provider": request.preferred_provider,
        "human_approved": False,
        "retry_count": 0,
        "current_step": "started",
        "logs": ["🚀 [Agent] Initializing autonomous SketchFlow pipeline stream..."]
    }

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield format_sse("started", {
                "thread_id": thread_id,
                "message": "SketchFlow agent pipeline initialized.",
                "initial_log": "🚀 [Agent] Initializing autonomous SketchFlow pipeline stream..."
            })

            async for chunk in agent_graph.astream(
                initial_state, config=config, stream_mode=["updates", "custom"], version="v2"
            ):
                chunk_type = chunk.get("type")
                chunk_data = chunk.get("data", {})

                if chunk_type == "custom":
                    event_kind = chunk_data.get("type", "custom")
                    if event_kind == "thought":
                        yield format_sse("thought", {
                            "thread_id": thread_id,
                            "step": chunk_data.get("step"),
                            "thought": chunk_data.get("thought"),
                            "timestamp": chunk_data.get("timestamp")
                        })
                    elif event_kind in ("tool_start", "tool_end"):
                        yield format_sse("tool_call", {
                            "thread_id": thread_id,
                            "event": event_kind,
                            "id": chunk_data.get("id"),
                            "tool": chunk_data.get("tool"),
                            "input": chunk_data.get("input"),
                            "output": chunk_data.get("output"),
                            "status": chunk_data.get("status", "running"),
                            "duration_ms": chunk_data.get("duration_ms")
                        })
                    else:
                        yield format_sse("custom_event", chunk_data)

                elif chunk_type == "updates":
                    for node_name, node_update in chunk_data.items():
                        if node_name == "__interrupt__":
                            continue
                        yield format_sse("node_update", {
                            "thread_id": thread_id,
                            "node": node_name,
                            "current_step": node_update.get("current_step"),
                            "logs": node_update.get("logs", []),
                            "sketch_graph": node_update.get("sketch_graph"),
                            "compiled_workflow": node_update.get("compiled_workflow"),
                            "layout_positions": node_update.get("layout_positions"),
                            "validation_report": node_update.get("validation_report"),
                            "tool_calls": node_update.get("tool_calls", []),
                            "reasoning_trace": node_update.get("reasoning_trace", []),
                            "deployment_result": node_update.get("deployment_result"),
                            "test_result": node_update.get("test_result"),
                            "execution_error": node_update.get("execution_error")
                        })

            # Checkpoint reached (paused at human review)
            state_record = agent_graph.get_state(config)
            state_values = state_record.values if state_record else {}
            yield format_sse("checkpoint", {
                "thread_id": thread_id,
                "status": state_values.get("current_step", "awaiting_review"),
                "sketch_graph": state_values.get("sketch_graph"),
                "compiled_workflow": state_values.get("compiled_workflow"),
                "layout_positions": state_values.get("layout_positions"),
                "validation_report": state_values.get("validation_report"),
                "tool_calls": state_values.get("tool_calls", []),
                "reasoning_trace": state_values.get("reasoning_trace", []),
                "logs": state_values.get("logs", [])
            })
            yield format_sse("done", {
                "thread_id": thread_id,
                "status": "paused_at_checkpoint"
            })

        except Exception as e:
            yield format_sse("error", {
                "thread_id": thread_id,
                "error": str(e)
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@router.post("/resume-stream", summary="Stream Agent Deployment & Self-Healing via SSE")
async def resume_agent_pipeline_stream(request: ResumeAgentRequest):
    """
    Resumes agent execution after human inspection.
    Streams deployment and self-healing telemetry in real time via SSE.
    """
    config = {"configurable": {"thread_id": request.thread_id}}

    current_state = agent_graph.get_state(config)
    if not current_state or not current_state.values:
        raise HTTPException(status_code=404, detail=f"No active session found for thread_id '{request.thread_id}'")

    resume_patch = {
        "human_approved": request.human_approved
    }
    if request.custom_parameters:
        resume_patch["custom_parameters"] = request.custom_parameters

    agent_graph.update_state(config, resume_patch)

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            yield format_sse("resumed", {
                "thread_id": request.thread_id,
                "message": "Agent execution resumed with human approval.",
                "human_approved": request.human_approved
            })

            async for chunk in agent_graph.astream(
                None, config=config, stream_mode=["updates", "custom"], version="v2"
            ):
                chunk_type = chunk.get("type")
                chunk_data = chunk.get("data", {})

                if chunk_type == "custom":
                    event_kind = chunk_data.get("type", "custom")
                    if event_kind == "thought":
                        yield format_sse("thought", {
                            "thread_id": request.thread_id,
                            "step": chunk_data.get("step"),
                            "thought": chunk_data.get("thought"),
                            "timestamp": chunk_data.get("timestamp")
                        })
                    elif event_kind in ("tool_start", "tool_end"):
                        yield format_sse("tool_call", {
                            "thread_id": request.thread_id,
                            "event": event_kind,
                            "id": chunk_data.get("id"),
                            "tool": chunk_data.get("tool"),
                            "input": chunk_data.get("input"),
                            "output": chunk_data.get("output"),
                            "status": chunk_data.get("status", "running"),
                            "duration_ms": chunk_data.get("duration_ms")
                        })
                    else:
                        yield format_sse("custom_event", chunk_data)

                elif chunk_type == "updates":
                    for node_name, node_update in chunk_data.items():
                        if node_name == "__interrupt__":
                            continue
                        yield format_sse("node_update", {
                            "thread_id": request.thread_id,
                            "node": node_name,
                            "current_step": node_update.get("current_step"),
                            "logs": node_update.get("logs", []),
                            "tool_calls": node_update.get("tool_calls", []),
                            "reasoning_trace": node_update.get("reasoning_trace", []),
                            "deployment_result": node_update.get("deployment_result"),
                            "test_result": node_update.get("test_result"),
                            "retry_count": node_update.get("retry_count"),
                            "execution_error": node_update.get("execution_error")
                        })

            state_record = agent_graph.get_state(config)
            state_values = state_record.values if state_record else {}
            yield format_sse("complete", {
                "thread_id": request.thread_id,
                "status": state_values.get("current_step", "completed"),
                "deployment_result": state_values.get("deployment_result"),
                "test_result": state_values.get("test_result"),
                "tool_calls": state_values.get("tool_calls", []),
                "reasoning_trace": state_values.get("reasoning_trace", []),
                "logs": state_values.get("logs", [])
            })
            yield format_sse("done", {
                "thread_id": request.thread_id,
                "status": "completed"
            })

        except Exception as e:
            yield format_sse("error", {
                "thread_id": request.thread_id,
                "error": str(e)
            })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

