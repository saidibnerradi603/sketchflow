"""
Experiment 04: Graph Compiler & Dynamic DAG Layout Engine
Compiles an extracted SketchGraph into an authoritative, valid n8n Workflow JSON:
1. Computes dynamic non-overlapping [x, y] coordinates via topological layering.
2. Synthesizes node parameters & n8n expressions using Nemotron-3-Ultra-550B (NVIDIA NIM)
   or OpenAI GPT-OSS 120B (Groq Cloud).
3. Connects edges with multi-output branching indices (main[0] True vs main[1] False).
"""

import os
import sys
import json
import uuid
import re
from typing import List, Dict, Any, Optional
from collections import defaultdict, deque

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

NVIDIA_API_KEY = os.getenv("NVIDIA_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

from pydantic import BaseModel, Field

class NodeParameterSpec(BaseModel):
    node_id: str = Field(description="The source sketch node ID (e.g. 'node_1')")
    n8n_name: str = Field(description="Human readable name in n8n, e.g. 'New Lead Webhook'")
    n8n_type: str = Field(description="Exact n8n type, e.g. 'n8n-nodes-base.webhook'")
    type_version: float = Field(default=2.0, description="n8n node typeVersion")
    parameters: Dict[str, Any] = Field(description="n8n node configuration parameters")

class WorkflowCompilationResult(BaseModel):
    workflow_name: str = Field(description="Clean, descriptive automation workflow name")
    nodes: List[NodeParameterSpec] = Field(description="All compiled n8n nodes")

SAMPLE_SKETCH_GRAPH = {
    "nodes": [
        {"id": "node_1", "label": "New Lead Webhook", "kind": "trigger", "shape": "rectangle"},
        {"id": "node_2", "label": "Is VIP?", "kind": "condition", "shape": "diamond"},
        {"id": "node_3", "label": "Send Slack Alert", "kind": "action", "shape": "rectangle"},
        {"id": "node_4", "label": "Log to Google Sheets", "kind": "action", "shape": "rectangle"}
    ],
    "edges": [
        {"from_id": "node_1", "to_id": "node_2", "label": None},
        {"from_id": "node_2", "to_id": "node_3", "label": "Yes"},
        {"from_id": "node_2", "to_id": "node_4", "label": "No"}
    ]
}

def compute_dag_positions(sketch_graph: dict) -> Dict[str, List[int]]:
    """
    Topological auto-layout:
    Assigns [x, y] coordinates to each node without overlaps.
    - X axis: graph depth / topological layer (280px step)
    - Y axis: vertical centering per layer (160px step)
    """
    nodes = {n["id"]: n for n in sketch_graph.get("nodes", [])}
    edges = sketch_graph.get("edges", [])
    
    adj = defaultdict(list)
    in_degree = {nid: 0 for nid in nodes}
    for e in edges:
        u, v = e.get("from_id"), e.get("to_id")
        if u in in_degree and v in in_degree:
            adj[u].append(v)
            in_degree[v] += 1

    # Breadth-first topological depth assignment
    layer = {}
    queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
    if not queue and nodes:
        queue.append(next(iter(nodes)))

    for nid in queue:
        layer[nid] = 0

    while queue:
        curr = queue.popleft()
        curr_layer = layer.get(curr, 0)
        for neighbor in adj[curr]:
            if neighbor not in layer or layer[neighbor] < curr_layer + 1:
                layer[neighbor] = curr_layer + 1
                queue.append(neighbor)

    for nid in nodes:
        if nid not in layer:
            layer[nid] = 0

    # Group nodes by layer to calculate Y offsets
    layer_groups = defaultdict(list)
    for nid, l in layer.items():
        layer_groups[l].append(nid)

    positions = {}
    base_x = 240
    base_y = 300
    x_gap = 300
    y_gap = 160

    for l, nids in layer_groups.items():
        x = base_x + l * x_gap
        count = len(nids)
        for idx, nid in enumerate(nids):
            y_offset = (idx - (count - 1) / 2.0) * y_gap
            positions[nid] = [int(x), int(base_y + y_offset)]

    return positions

def clean_json_output(raw_text: str) -> str:
    text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text

def synthesize_parameters_with_langchain(sketch_graph: dict) -> Optional[WorkflowCompilationResult]:
    """
    Calls LangChain to synthesize authoritative n8n configurations
    Primary: NVIDIA NEMOTRON-3-ULTRA-550B
    Fallback: Groq OPENAI GPT-OSS 120B
    """
    try:
        from langchain_core.messages import HumanMessage
        from langchain.chat_models import init_chat_model
    except ImportError:
        print("⚠️ LangChain is not installed yet.")
        return None

    schema_str = json.dumps(WorkflowCompilationResult.model_json_schema(), indent=2)
    prompt = f"""You are a master n8n workflow architect.
Convert this extracted diagram graph into fully functional, production-ready n8n nodes:
{json.dumps(sketch_graph, indent=2)}

Rules for n8n node types:
- Webhook trigger -> 'n8n-nodes-base.webhook', typeVersion: 2, parameters: {{"httpMethod": "POST", "path": "lead-intake", "responseMode": "onReceived"}}
- Condition / Diamond -> 'n8n-nodes-base.if', typeVersion: 2.2, parameters: {{"conditions": {{"options": {{"caseSensitive": true}}, "conditions": [{{"id": "cond_1", "leftValue": "={{ $json.body.is_vip }}", "rightValue": true, "operator": {{"type": "boolean", "operation": "equals"}}}}]}}}}
- Slack notification -> 'n8n-nodes-base.slack', typeVersion: 2.2, parameters: {{"select": "channel", "channelId": "alerts", "text": "=🌟 VIP Lead Intake: {{{{ $json.body.name || 'Anonymous' }}}} (Email: {{{{ $json.body.email || 'N/A' }}}})" }}
- Google Sheets / Database -> 'n8n-nodes-base.googleSheets', typeVersion: 4.5, parameters: {{"operation": "append", "sheetName": "Leads", "fieldsUi": {{"fieldValues": [{{"fieldId": "Name", "fieldValue": "={{ $json.body.name }}"}}]}}}}

You MUST output ONLY a valid JSON object conforming to this schema:
{schema_str}
"""

    message = HumanMessage(content=prompt)

    # 1. Primary: NVIDIA NIM (Nemotron-3-Ultra-550B)
    if NVIDIA_API_KEY and not NVIDIA_API_KEY.startswith("your_"):
        print("[Compiler] Synthesizing parameters with NVIDIA NIM (nvidia/nemotron-3-ultra-550b-a55b)...")
        try:
            llm = init_chat_model(
                model="nvidia/nemotron-3-ultra-550b-a55b",
                model_provider="nvidia",
                api_key=NVIDIA_API_KEY,
                temperature=0.1
            )
            response = llm.invoke([message])
            cleaned = clean_json_output(response.content)
            result = WorkflowCompilationResult.model_validate_json(cleaned)
            print("✅ NVIDIA NIM compiler synthesized successfully!")
            return result
        except Exception as e:
            print(f"⚠️ NVIDIA compiler error: {e}. Falling back to Groq...")

    # 2. Fallback: Groq Cloud (openai/gpt-oss-120b)
    if GROQ_API_KEY and not GROQ_API_KEY.startswith("your_"):
        print("[Compiler] Synthesizing parameters with Groq (openai/gpt-oss-120b)...")
        try:
            llm = init_chat_model(
                model="openai/gpt-oss-120b",
                model_provider="groq",
                api_key=GROQ_API_KEY,
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            response = llm.invoke([message])
            cleaned = clean_json_output(response.content)
            result = WorkflowCompilationResult.model_validate_json(cleaned)
            print("✅ Groq GPT-OSS 120B compiler synthesized successfully!")
            return result
        except Exception as e:
            print(f"❌ Groq compiler error: {e}")

    return None

def assemble_n8n_payload(sketch_graph: dict, synthesized_result: Optional[WorkflowCompilationResult] = None) -> dict:
    positions = compute_dag_positions(sketch_graph)
    nodes_info = {n["id"]: n for n in sketch_graph.get("nodes", [])}
    
    n8n_nodes = []
    id_to_name = {}
    node_kind_map = {}

    if synthesized_result and synthesized_result.nodes:
        for item in synthesized_result.nodes:
            pos = positions.get(item.node_id, [240, 300])
            id_to_name[item.node_id] = item.n8n_name
            node_kind_map[item.node_id] = nodes_info.get(item.node_id, {}).get("kind", "action")
            n8n_nodes.append({
                "id": str(uuid.uuid4()),
                "name": item.n8n_name,
                "type": item.n8n_type,
                "typeVersion": item.type_version,
                "position": pos,
                "parameters": item.parameters
            })
    else:
        # Fallback deterministic definitions
        defaults = {
            "node_1": ("New Lead Webhook", "n8n-nodes-base.webhook", 2.0, {"httpMethod": "POST", "path": "lead-intake", "responseMode": "onReceived"}),
            "node_2": ("Is VIP?", "n8n-nodes-base.if", 2.2, {"conditions": {"conditions": [{"leftValue": "={{ $json.body.is_vip }}", "rightValue": True, "operator": {"type": "boolean", "operation": "equals"}}]}}),
            "node_3": ("Send Slack Alert", "n8n-nodes-base.slack", 2.2, {"select": "channel", "channelId": "alerts", "text": "=🌟 VIP Lead: {{ $json.body.name }}"}),
            "node_4": ("Log to Google Sheets", "n8n-nodes-base.googleSheets", 4.5, {"operation": "append", "sheetName": "Leads"})
        }
        for nid, node_data in nodes_info.items():
            name, n_type, v, params = defaults.get(nid, (node_data.get("label", nid), "n8n-nodes-base.code", 2.0, {}))
            pos = positions.get(nid, [240, 300])
            id_to_name[nid] = name
            node_kind_map[nid] = node_data.get("kind", "action")
            n8n_nodes.append({
                "id": str(uuid.uuid4()),
                "name": name,
                "type": n_type,
                "typeVersion": v,
                "position": pos,
                "parameters": params
            })

    # Build n8n connections with true/false branch indexing
    connections = defaultdict(lambda: {"main": []})
    
    # Track condition branches
    for edge in sketch_graph.get("edges", []):
        u, v = edge.get("from_id"), edge.get("to_id")
        lbl = str(edge.get("label") or "").strip().lower()
        if u not in id_to_name or v not in id_to_name:
            continue
        
        src_name = id_to_name[u]
        tgt_name = id_to_name[v]
        src_kind = node_kind_map.get(u, "action")

        target_conn = {"node": tgt_name, "type": "main", "index": 0}

        if src_kind == "condition" or "if" in src_name.lower():
            # n8n IF node: main[0] = True, main[1] = False
            is_false_branch = (lbl in ["no", "false", "f", "0"])
            branch_idx = 1 if is_false_branch else 0
            
            # Ensure outer list has enough slots
            while len(connections[src_name]["main"]) <= branch_idx:
                connections[src_name]["main"].append([])
            connections[src_name]["main"][branch_idx].append(target_conn)
        else:
            # Standard single-output node
            if not connections[src_name]["main"]:
                connections[src_name]["main"].append([])
            connections[src_name]["main"][0].append(target_conn)

    workflow_name = synthesized_result.workflow_name if synthesized_result else "SketchFlow Intake Pipeline"
    
    return {
        "name": workflow_name,
        "nodes": n8n_nodes,
        "connections": dict(connections),
        "settings": {"executionOrder": "v1"}
    }

if __name__ == "__main__":
    print("="*60)
    print("Testing LangChain Graph Compiler & Dynamic Auto-Layout Engine")
    print("="*60)
    
    synth = synthesize_parameters_with_langchain(SAMPLE_SKETCH_GRAPH)
    payload = assemble_n8n_payload(SAMPLE_SKETCH_GRAPH, synth)
    
    output_path = "experiments/compiled_workflow.json"
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2)
        
    print(f"\n✅ Compiled n8n JSON successfully saved to: {output_path}")
    print(f"Workflow Name: {payload['name']}")
    print(f"Total Nodes: {len(payload['nodes'])}")
    print(f"Connections Map: {json.dumps(payload['connections'], indent=2)}")
