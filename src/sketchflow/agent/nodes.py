"""
StateGraph Nodes for SketchFlow.

Implements the perception, compilation, human review, deployment,
and self-healing transitions with real-time LangGraph StreamWriter events.

Key capabilities:
- Real time.perf_counter() measurements
- Real-time StreamWriter emissions for agent thoughts and tool calls
- try/except around deploy with webhook mount readiness delay
- REAL LLM-powered self-healing via REPAIR_SYSTEM_PROMPT
- Full 100+ node catalog integration
"""

import re
import json
import time
import asyncio
from typing import Dict, Any, List, Optional

try:
    from langgraph.types import StreamWriter
except ImportError:
    StreamWriter = Any

from sketchflow.agent.state import SketchFlowState
from sketchflow.agent.tools import (
    validate_n8n_workflow,
    inspect_node_schema,
    calculate_dag_layout,
    search_n8n_docs,
)
from sketchflow.services.vision_service import VisionService
from sketchflow.services.compiler_service import CompilerService
from sketchflow.services.n8n_service import N8nService

vision_service = VisionService()
compiler_service = CompilerService()
n8n_service = N8nService()


def _clean_json_output(raw_text: str) -> str:
    """Strips markdown code fences and whitespace from LLM output."""
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text


def _emit(arg1: Any, arg2: Any = None) -> None:
    """Safely emits a custom streaming event through LangGraph's StreamWriter."""
    if isinstance(arg1, dict):
        event = arg1
        writer = arg2
    else:
        writer = arg1
        event = arg2 or {}

    if writer:
        try:
            writer(event)
            return
        except Exception:
            pass
    try:
        from langgraph.config import get_stream_writer
        w = get_stream_writer()
        w(event)
    except Exception:
        pass


# Perception Node
async def perceive_node(
    state: SketchFlowState,
    writer: Optional[StreamWriter] = None
) -> Dict[str, Any]:
    """Extracts diagram topology from image using multimodal Vision-Language Model."""
    logs = list(state.get("logs", []))
    tools = list(state.get("tool_calls", []))
    reasoning = list(state.get("reasoning_trace", []))

    thought_text = (
        f"Analyzing diagram drawing with VLM "
        f"({state.get('preferred_provider') or 'nvidia'}) to extract "
        f"topological nodes, labels, and directed connections."
    )
    logs.append("🔍 [Perception] Extracting diagram graph from image...")
    reasoning.append({
        "step": "perception",
        "thought": thought_text,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "perception",
        "thought": thought_text,
    })

    tool_input = {
        "provider": state.get("preferred_provider") or "nvidia",
        "input_mode": "base64" if state.get("image_base64") else "file_path",
    }
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-vlm-1",
        "tool": "vlm_multimodal_extractor",
        "input": tool_input,
    })

    t0 = time.perf_counter()

    if state.get("image_base64"):
        res = vision_service.extract_from_base64(
            state["image_base64"],
            preferred_provider=state.get("preferred_provider"),
        )
    elif state.get("image_path"):
        res = vision_service.extract_from_file(
            state["image_path"],
            preferred_provider=state.get("preferred_provider"),
        )
    else:
        raise ValueError(
            "Neither image_base64 nor image_path provided to perception_node."
        )

    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    logs.append(
        f"✅ [Perception] Extracted {res.total_nodes} nodes and "
        f"{res.total_edges} connections using {res.model_used} "
        f"({res.latency_seconds}s)"
    )

    tool_call_data = {
        "tool": "vlm_multimodal_extractor",
        "input": tool_input,
        "output": {
            "nodes_extracted": res.total_nodes,
            "edges_extracted": res.total_edges,
            "latency_seconds": res.latency_seconds,
            "model_used": res.model_used,
        },
        "status": "success",
        "duration_ms": elapsed_ms,
    }
    tools.append(tool_call_data)
    _emit(writer, {
        "type": "tool_end",
        "id": "tool-vlm-1",
        **tool_call_data,
    })

    return {
        "sketch_graph": res.graph,
        "perception_model": res.model_used,
        "perception_latency": res.latency_seconds,
        "current_step": "perceived",
        "logs": logs,
        "tool_calls": tools,
        "reasoning_trace": reasoning,
    }


# Compilation Node
async def compile_node(
    state: SketchFlowState,
    writer: Optional[StreamWriter] = None
) -> Dict[str, Any]:
    """Synthesizes workflow schema, computes topological DAG layout, and validates connections."""
    logs = list(state.get("logs", []))
    tools = list(state.get("tool_calls", []))
    reasoning = list(state.get("reasoning_trace", []))

    thought_text = (
        "Synthesizing n8n workflow definition from diagram graph. "
        "Resolving node types via catalog, mapping topological DAG layout "
        "coordinates, and validating connections."
    )
    logs.append(
        "📐 [Compiler] Computing topological DAG layout & synthesizing "
        "node schemas..."
    )
    reasoning.append({
        "step": "compilation",
        "thought": thought_text,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "compilation",
        "thought": thought_text,
    })

    graph = state.get("sketch_graph")
    if not graph:
        raise ValueError("Cannot compile: sketch_graph is missing from state.")

    schema_input = {"nodes": [n.label for n in graph.nodes]}
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-schema-1",
        "tool": "inspect_node_schema",
        "input": schema_input,
    })

    t0 = time.perf_counter()
    mapped_nodes = []
    for n in graph.nodes:
        schema_info = inspect_node_schema(n.label)
        n8n_type = schema_info.get("n8n_type", "n8n-nodes-base.code")
        mapped_nodes.append({
            "label": n.label,
            "n8n_type": n8n_type,
            "found": schema_info.get("found", False),
            "matched_keyword": schema_info.get("matched_keyword"),
        })
    schema_ms = int((time.perf_counter() - t0) * 1000)

    schema_call_data = {
        "tool": "inspect_node_schema",
        "input": schema_input,
        "output": {
            "mapped_types": mapped_nodes,
            "total_mapped": len(mapped_nodes),
        },
        "status": "success",
        "duration_ms": schema_ms,
    }
    tools.append(schema_call_data)
    _emit(writer, {
        "type": "tool_end",
        "id": "tool-schema-1",
        **schema_call_data,
    })

    docs_context = None
    unrecognized = [m for m in mapped_nodes if not m.get("found")]
    if unrecognized:
        target_label = unrecognized[0]["label"]
        doc_thought = (
            f"Node '{target_label}' is not in the direct catalog. "
            f"Querying official n8n documentation (docs.n8n.io) via search_n8n_docs for specs..."
        )
        logs.append(f"📚 [Compiler] Searching n8n documentation for '{target_label}'...")
        reasoning.append({
            "step": "compilation",
            "thought": doc_thought,
            "timestamp": time.time(),
        })
        _emit(writer, {
            "type": "thought",
            "step": "compilation",
            "thought": doc_thought,
        })

        doc_input = {"query": target_label}
        _emit(writer, {
            "type": "tool_start",
            "id": "tool-doc-1",
            "tool": "search_n8n_docs",
            "input": doc_input,
        })
        t0_doc = time.perf_counter()
        doc_content = await search_n8n_docs(target_label)
        docs_context = doc_content
        doc_ms = int((time.perf_counter() - t0_doc) * 1000)

        doc_call_data = {
            "tool": "search_n8n_docs",
            "input": doc_input,
            "output": {
                "content": doc_content,
                "length_chars": len(doc_content),
                "source": "docs.n8n.io",
            },
            "status": "success",
            "duration_ms": doc_ms,
        }
        tools.append(doc_call_data)
        _emit(writer, {
            "type": "tool_end",
            "id": "tool-doc-1",
            **doc_call_data,
        })

    _emit(writer, {
        "type": "thought",
        "step": "compilation",
        "thought": (
            f"Querying LLM compiler to synthesize production parameters "
            f"and expressions for {len(graph.nodes)} workflow nodes."
        ),
    })

    t0 = time.perf_counter()
    res = compiler_service.compile(
        graph=graph,
        workflow_name=state.get("workflow_name"),
        custom_parameters=state.get("custom_parameters"),
        docs_context=docs_context,
    )
    compile_ms = int((time.perf_counter() - t0) * 1000)

    dag_input = {
        "nodes_count": len(graph.nodes),
        "edges_count": len(graph.edges),
        "algorithm": "topological_layered_grid",
    }
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-dag-1",
        "tool": "calculate_dag_layout",
        "input": dag_input,
    })

    t0 = time.perf_counter()
    positions = compiler_service.compute_dag_positions(graph)
    layout_ms = int((time.perf_counter() - t0) * 1000)

    dag_call_data = {
        "tool": "calculate_dag_layout",
        "input": dag_input,
        "output": {"positions": positions},
        "status": "success",
        "duration_ms": layout_ms,
    }
    tools.append(dag_call_data)
    _emit(writer, {
        "type": "tool_end",
        "id": "tool-dag-1",
        **dag_call_data,
    })

    lint_input = {
        "workflow_name": res.workflow.name,
        "nodes_count": res.node_count,
        "connections_count": len(res.workflow.connections),
    }
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-lint-1",
        "tool": "validate_n8n_workflow",
        "input": lint_input,
    })

    t0 = time.perf_counter()
    workflow_dict = res.workflow.model_dump()
    linter_report = validate_n8n_workflow(workflow_dict)
    lint_ms = int((time.perf_counter() - t0) * 1000)

    lint_call_data = {
        "tool": "validate_n8n_workflow",
        "input": lint_input,
        "output": linter_report,
        "status": "success" if linter_report.get("valid") else "warning",
        "duration_ms": lint_ms,
    }
    tools.append(lint_call_data)
    _emit(writer, {
        "type": "tool_end",
        "id": "tool-lint-1",
        **lint_call_data,
    })

    linter_status = "PASSED" if linter_report.get("valid") else "WARNINGS"
    logs.append(
        f"✅ [Compiler] Successfully compiled workflow '{res.workflow.name}' "
        f"with {res.node_count} nodes in {compile_ms}ms. "
        f"Linter: {linter_status}"
    )
    if res.synthesizer_model:
        logs.append(f"   └─ LLM synthesizer: {res.synthesizer_model}")

    summary_thought = (
        f"Compiled '{res.workflow.name}' with {res.node_count} nodes and "
        f"{len(res.workflow.connections)} connections. "
        f"Linter: {linter_status}. "
        f"Synthesizer: {res.synthesizer_model or 'deterministic fallback'}."
    )
    reasoning.append({
        "step": "compilation",
        "thought": summary_thought,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "compilation",
        "thought": summary_thought,
    })

    return {
        "compiled_workflow": res.workflow,
        "layout_positions": positions,
        "validation_report": linter_report,
        "current_step": "compiled",
        "logs": logs,
        "tool_calls": tools,
        "reasoning_trace": reasoning,
    }


# Human-in-the-Loop Review Node
async def human_review_node(
    state: SketchFlowState,
    writer: Optional[StreamWriter] = None
) -> Dict[str, Any]:
    """Human-in-the-Loop checkpoint: pauses execution until user inspects and approves workflow."""
    logs = list(state.get("logs", []))
    tools = list(state.get("tool_calls", []))
    reasoning = list(state.get("reasoning_trace", []))

    if not state.get("human_approved", False):
        logs.append(
            "⏸️ [Review] Pausing at checkpoint for user inspection "
            "and parameter configuration."
        )
        thought_text = (
            "Pausing execution pipeline at Human-in-the-Loop review "
            "checkpoint. Awaiting user inspection, credential binding, "
            "and explicit approval before deploying to n8n."
        )
        step = "awaiting_review"
    else:
        logs.append(
            "👍 [Review] User approved workflow with custom configurations. "
            "Proceeding to deploy."
        )
        thought_text = (
            "Operator approved workflow configuration. Injecting "
            "customized parameters/credentials and proceeding to deployment."
        )
        step = "approved"

    reasoning.append({
        "step": "human_review",
        "thought": thought_text,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "human_review",
        "thought": thought_text,
    })

    return {
        "current_step": step,
        "logs": logs,
        "tool_calls": tools,
        "reasoning_trace": reasoning,
    }


# Deployment & Live Verification Node
async def deploy_node(
    state: SketchFlowState,
    writer: Optional[StreamWriter] = None
) -> Dict[str, Any]:
    """
    Deployment & Live Verification Node.
    Deploys the compiled workflow to n8n via REST API, then optionally
    fires a synthetic webhook event for closed-loop verification.
    """
    logs = list(state.get("logs", []))
    tools = list(state.get("tool_calls", []))
    reasoning = list(state.get("reasoning_trace", []))

    workflow = state.get("compiled_workflow")
    if not workflow:
        raise ValueError("Cannot deploy: compiled_workflow is missing.")

    deploy_thought = (
        f"Deploying synthesized workflow '{workflow.name}' to n8n "
        f"server REST API (activate=True)."
    )
    logs.append(
        f"🚀 [Deployment] Uploading '{workflow.name}' to local n8n instance..."
    )
    reasoning.append({
        "step": "deployment",
        "thought": deploy_thought,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "deployment",
        "thought": deploy_thought,
    })

    deploy_input = {
        "workflow_name": workflow.name,
        "node_count": len(workflow.nodes),
        "activate": True,
    }
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-deploy-1",
        "tool": "deploy_workflow",
        "input": deploy_input,
    })

    t0 = time.perf_counter()
    try:
        deploy_res = await n8n_service.deploy_workflow(workflow, activate=True)
    except Exception as e:
        deploy_ms = int((time.perf_counter() - t0) * 1000)
        exec_error = f"n8n deployment failed: {str(e)}"
        logs.append(f"❌ [Deployment] {exec_error}")

        fail_thought = (
            f"Deployment HTTP call failed after {deploy_ms}ms: {str(e)}. "
            f"Routing to self-healing node for automated remediation."
        )
        reasoning.append({
            "step": "deployment",
            "thought": fail_thought,
            "timestamp": time.time(),
        })
        _emit(writer, {
            "type": "thought",
            "step": "deployment",
            "thought": fail_thought,
        })

        fail_call_data = {
            "tool": "deploy_workflow",
            "input": deploy_input,
            "output": {"error": str(e)},
            "status": "error",
            "duration_ms": deploy_ms,
        }
        tools.append(fail_call_data)
        _emit(writer, {
            "type": "tool_end",
            "id": "tool-deploy-1",
            **fail_call_data,
        })

        return {
            "deployment_result": None,
            "test_result": None,
            "execution_error": exec_error,
            "current_step": "deploy_failed",
            "logs": logs,
            "tool_calls": tools,
            "reasoning_trace": reasoning,
        }

    deploy_ms = int((time.perf_counter() - t0) * 1000)
    logs.append(
        f"🟢 [Deployment] Workflow active with ID: {deploy_res.workflow_id}"
    )

    deploy_call_data = {
        "tool": "deploy_workflow",
        "input": deploy_input,
        "output": {
            "workflow_id": deploy_res.workflow_id,
            "active": deploy_res.active,
            "webhook_urls": deploy_res.webhook_urls,
            "status": "deployed",
        },
        "status": "success" if deploy_res.workflow_id else "error",
        "duration_ms": deploy_ms,
    }
    tools.append(deploy_call_data)
    _emit(writer, {
        "type": "tool_end",
        "id": "tool-deploy-1",
        **deploy_call_data,
    })

    test_res = None
    exec_error = None

    if deploy_res.webhook_urls:
        target_url = deploy_res.webhook_urls[0]
        slug = target_url.split("/")[-1]
        verify_thought = (
            f"Conducting live closed-loop test by dispatching synthetic "
            f"JSON payload to webhook endpoint '/webhook/{slug}'."
        )
        logs.append(
            f"⚡ [Live Verification] Firing synthetic event to "
            f"webhook '{slug}'..."
        )
        reasoning.append({
            "step": "verification",
            "thought": verify_thought,
            "timestamp": time.time(),
        })
        _emit(writer, {
            "type": "thought",
            "step": "verification",
            "thought": verify_thought,
        })

        test_payload = {"source": "sketchflow_agent", "status": "active"}
        test_input = {
            "webhook_slug": slug,
            "method": "POST",
            "payload": test_payload,
        }
        _emit(writer, {
            "type": "tool_start",
            "id": "tool-test-1",
            "tool": "test_webhook",
            "input": test_input,
        })

        await asyncio.sleep(1.2)

        t0 = time.perf_counter()
        test_res = await n8n_service.test_webhook(slug, test_payload)

        if not test_res.success and test_res.status_code == 404:
            await asyncio.sleep(1.5)
            test_res = await n8n_service.test_webhook(slug, test_payload)

        test_ms = int((time.perf_counter() - t0) * 1000)
        latency_val = getattr(test_res, "latency_ms", None) or test_ms

        test_call_data = {
            "tool": "test_webhook",
            "input": test_input,
            "output": {
                "status_code": test_res.status_code,
                "latency_ms": latency_val,
                "response": test_res.response_data,
            },
            "status": "success" if test_res.success else "warning",
            "duration_ms": test_ms,
        }
        tools.append(test_call_data)
        _emit(writer, {
            "type": "tool_end",
            "id": "tool-test-1",
            **test_call_data,
        })

        if test_res.success:
            logs.append(
                f"🎉 [Live Verification] Success! Webhook responded: "
                f"{test_res.response_data}"
            )
            success_thought = (
                f"Closed-loop verification succeeded. Webhook responded "
                f"with status {test_res.status_code} in {latency_val}ms."
            )
            reasoning.append({
                "step": "verification",
                "thought": success_thought,
                "timestamp": time.time(),
            })
            _emit(writer, {
                "type": "thought",
                "step": "verification",
                "thought": success_thought,
            })
        else:
            exec_error = (
                f"Webhook error ({test_res.status_code}): "
                f"{test_res.response_data}"
            )
            logs.append(f"⚠️ [Live Verification] Issue detected: {exec_error}")
            fail_verify_thought = (
                f"Live verification returned status {test_res.status_code}. "
                f"Initiating automated self-healing analysis."
            )
            reasoning.append({
                "step": "verification",
                "thought": fail_verify_thought,
                "timestamp": time.time(),
            })
            _emit(writer, {
                "type": "thought",
                "step": "verification",
                "thought": fail_verify_thought,
            })

    return {
        "deployment_result": deploy_res,
        "test_result": test_res,
        "execution_error": exec_error,
        "current_step": "deployed",
        "logs": logs,
        "tool_calls": tools,
        "reasoning_trace": reasoning,
    }


# Self-Healing Reflection Node
async def self_heal_node(
    state: SketchFlowState,
    writer: Optional[StreamWriter] = None
) -> Dict[str, Any]:
    """Analyzes runtime errors with LLM reflection and synthesizes a repaired workflow definition."""
    logs = list(state.get("logs", []))
    tools = list(state.get("tool_calls", []))
    reasoning = list(state.get("reasoning_trace", []))

    retries = state.get("retry_count", 0) + 1
    err = state.get("execution_error", "Unknown error")
    workflow = state.get("compiled_workflow")

    logs.append(
        f"🔧 [Self-Healing] (Attempt {retries}/2) Analyzing error: {err}"
    )

    workflow_dict = workflow.model_dump() if workflow else {}
    repair_context = (
        f"## Failed Workflow JSON\n"
        f"```json\n{json.dumps(workflow_dict, indent=2)}\n```\n\n"
        f"## Error from n8n\n{err}\n\n"
        f"Analyze this error and produce a corrected workflow JSON "
        f"following the output contract exactly."
    )

    heal_thought = (
        f"Self-healing attempt {retries}/2: Preparing LLM repair call "
        f"with full workflow context and error message. "
        f"Error: '{err[:200]}'"
    )
    reasoning.append({
        "step": "self_healing",
        "thought": heal_thought,
        "timestamp": time.time(),
    })
    _emit(writer, {
        "type": "thought",
        "step": "self_healing",
        "thought": heal_thought,
    })

    repair_input = {
        "error": err[:500],
        "workflow_nodes": len(workflow_dict.get("nodes", [])),
    }
    _emit(writer, {
        "type": "tool_start",
        "id": "tool-repair-1",
        "tool": "llm_repair_engine",
        "input": repair_input,
    })

    repair_result = None
    repair_model = None
    t0 = time.perf_counter()

    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain.chat_models import init_chat_model
        from sketchflow.agent.prompts import REPAIR_SYSTEM_PROMPT
        from sketchflow.core.config import settings

        repair_messages = [
            SystemMessage(content=REPAIR_SYSTEM_PROMPT),
            HumanMessage(content=repair_context),
        ]

        for provider_config in [
            {
                "key": settings.NVIDIA_API_KEY,
                "model": settings.NVIDIA_COMPILER_MODEL,
                "provider": "nvidia",
                "extra": {},
            },
            {
                "key": settings.GROQ_API_KEY,
                "model": settings.GROQ_COMPILER_MODEL,
                "provider": "groq",
                "extra": {"model_kwargs": {"response_format": {"type": "json_object"}}},
            },
        ]:
            if not provider_config["key"]:
                continue
            try:
                llm = init_chat_model(
                    model=provider_config["model"],
                    model_provider=provider_config["provider"],
                    api_key=provider_config["key"],
                    temperature=0.1,
                    **provider_config["extra"],
                )
                response = llm.invoke(repair_messages)
                parsed = json.loads(_clean_json_output(response.content))
                if isinstance(parsed, dict):
                    repair_result = parsed
                    repair_model = provider_config["model"]
                    break
            except Exception:
                continue

    except ImportError:
        logs.append(
            "⚠️ [Self-Healing] LLM libraries not available for repair."
        )

    repair_ms = int((time.perf_counter() - t0) * 1000)

    # ── Step 3: Apply LLM repair result ──
    if repair_result and "full_corrected_workflow" in repair_result:
        from sketchflow.schemas.workflow import N8nWorkflowDTO

        try:
            corrected = N8nWorkflowDTO.model_validate(
                repair_result["full_corrected_workflow"]
            )
            workflow = corrected
            diagnosis = repair_result.get("diagnosis", "LLM auto-repair")
            patched_node = repair_result.get(
                "patched_node_name", "unknown"
            )

            logs.append(
                f"🩹 [Self-Healing] Diagnosis: {diagnosis}"
            )
            logs.append(
                f"✅ [Self-Healing] Patched node: {patched_node} "
                f"(model: {repair_model})"
            )

            repair_call_data = {
                "tool": "llm_repair_engine",
                "input": {**repair_input, "model": repair_model},
                "output": {
                    "diagnosis": diagnosis,
                    "patched_node": patched_node,
                    "patched_fields": repair_result.get("patched_fields", []),
                    "repair_successful": True,
                },
                "status": "success",
                "duration_ms": repair_ms,
            }
            tools.append(repair_call_data)
            _emit(writer, {
                "type": "tool_end",
                "id": "tool-repair-1",
                **repair_call_data,
            })

            post_heal_thought = (
                f"LLM repair succeeded. Diagnosis: {diagnosis}. "
                f"Patched node: {patched_node}. Model: {repair_model}. "
                f"Retrying deployment with corrected workflow."
            )
            reasoning.append({
                "step": "self_healing",
                "thought": post_heal_thought,
                "timestamp": time.time(),
            })
            _emit(writer, {
                "type": "thought",
                "step": "self_healing",
                "thought": post_heal_thought,
            })

        except Exception as e:
            logs.append(
                f"⚠️ [Self-Healing] LLM produced response but validation failed: {str(e)}"
            )
            fail_repair_data = {
                "tool": "llm_repair_engine",
                "input": {**repair_input, "model": repair_model},
                "output": {"repair_successful": False, "reason": str(e)},
                "status": "warning",
                "duration_ms": repair_ms,
            }
            tools.append(fail_repair_data)
            _emit(writer, {
                "type": "tool_end",
                "id": "tool-repair-1",
                **fail_repair_data,
            })

    elif repair_result:
        diagnosis = repair_result.get("diagnosis", "Analysis only")
        logs.append(
            f"ℹ️ [Self-Healing] LLM diagnosis: {diagnosis} (no corrected workflow produced)"
        )
        partial_repair_data = {
            "tool": "llm_repair_engine",
            "input": {**repair_input, "model": repair_model},
            "output": {
                "diagnosis": diagnosis,
                "repair_successful": False,
                "reason": "No full_corrected_workflow in response",
            },
            "status": "warning",
            "duration_ms": repair_ms,
        }
        tools.append(partial_repair_data)
        _emit(writer, {
            "type": "tool_end",
            "id": "tool-repair-1",
            **partial_repair_data,
        })

    else:
        logs.append(
            "⚠️ [Self-Healing] LLM repair did not produce a usable result. Retrying workflow as-is."
        )
        empty_repair_data = {
            "tool": "llm_repair_engine",
            "input": repair_input,
            "output": {"repair_successful": False, "reason": "No LLM response"},
            "status": "error",
            "duration_ms": repair_ms,
        }
        tools.append(empty_repair_data)
        _emit(writer, {
            "type": "tool_end",
            "id": "tool-repair-1",
            **empty_repair_data,
        })

    return {
        "compiled_workflow": workflow,
        "execution_error": None,
        "retry_count": retries,
        "current_step": "self_healed",
        "logs": logs,
        "tool_calls": tools,
        "reasoning_trace": reasoning,
    }
