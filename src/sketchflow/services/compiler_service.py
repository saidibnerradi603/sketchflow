"""
Compiler Service for converting a SketchGraph into a valid n8n Workflow JSON payload.
1. Computes non-overlapping [x, y] coordinates via dynamic topological layering.
2. Uses Nemotron-3-Ultra-550B (or Groq GPT-OSS 120B) for parameter synthesis.
3. Maps multi-output branching indices (main[0] True vs main[1] False).
"""

import os
import re
import json
import uuid
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict, deque

from sketchflow.core.config import settings, Settings
from sketchflow.schemas.diagram import SketchGraph, SketchNode
from sketchflow.schemas.workflow import (
    N8nNodeDTO,
    N8nWorkflowDTO,
    CompileWorkflowResponse
)

class CompilerService:
    """Service to compile diagrams into authoritative, production-ready n8n workflows."""

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or settings

    def compute_dag_positions(self, graph: SketchGraph) -> Dict[str, List[int]]:
        """
        Calculates [x, y] coordinates on the n8n canvas using topological layering.
        - X axis: graph depth / topological layer (300px step)
        - Y axis: vertical centering per layer (160px step)
        """
        nodes = {n.id: n for n in graph.nodes}
        if not nodes:
            return {}

        adj = defaultdict(list)
        in_degree = {nid: 0 for nid in nodes}
        for e in graph.edges:
            if e.from_id in in_degree and e.to_id in in_degree:
                adj[e.from_id].append(e.to_id)
                in_degree[e.to_id] += 1

        # Breadth-first topological layer assignment
        layer = {}
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        if not queue and nodes:
            queue.append(next(iter(nodes)))

        for nid in queue:
            layer[nid] = 0

        visited_count = 0
        while queue and visited_count < len(nodes) * 2:
            curr = queue.popleft()
            visited_count += 1
            curr_layer = layer.get(curr, 0)
            for neighbor in adj[curr]:
                if neighbor not in layer or layer[neighbor] < curr_layer + 1:
                    layer[neighbor] = curr_layer + 1
                    queue.append(neighbor)

        # Fallback for disconnected nodes
        for nid in nodes:
            if nid not in layer:
                layer[nid] = 0

        # Group nodes by layer to calculate vertical offsets
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

    def _clean_json_output(self, raw_text: str) -> str:
        text = raw_text.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            return match.group(1).strip()
        return text

    def _synthesize_parameters_with_llm(
        self,
        graph: SketchGraph,
        custom_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        docs_context: Optional[str] = None
    ) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str], Optional[str]]:
        """
        Calls LLM to determine authoritative n8n node types and configuration parameters.
        Returns (nodes_list, workflow_name, model_used).
        """
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain.chat_models import init_chat_model
        from sketchflow.agent.prompts import COMPILER_SYSTEM_PROMPT

        graph_dict = graph.model_dump()
        user_prompt = (
            f"Here is the extracted workflow diagram graph:\n"
            f"{json.dumps(graph_dict, indent=2)}\n\n"
        )
        if docs_context:
            user_prompt += (
                f"### Official n8n Documentation Context (retrieved for unmapped/specialized nodes):\n"
                f"{docs_context}\n\n"
                f"Use this official documentation to synthesize authoritative n8n node types, "
                f"exact parameters, and valid expressions for any matching nodes.\n\n"
            )
        user_prompt += "Synthesize production-grade n8n node definitions for each node."

        messages = [
            SystemMessage(content=COMPILER_SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]

        # 1. Try NVIDIA NIM
        if self.config.NVIDIA_API_KEY:
            try:
                llm = init_chat_model(
                    model=self.config.NVIDIA_COMPILER_MODEL,
                    model_provider="nvidia",
                    api_key=self.config.NVIDIA_API_KEY,
                    temperature=0.1
                )
                res = llm.invoke(messages)
                data = json.loads(self._clean_json_output(res.content))
                return data.get("nodes"), data.get("workflow_name"), self.config.NVIDIA_COMPILER_MODEL
            except Exception:
                pass

        # 2. Try Groq Cloud
        if self.config.GROQ_API_KEY:
            try:
                llm = init_chat_model(
                    model=self.config.GROQ_COMPILER_MODEL,
                    model_provider="groq",
                    api_key=self.config.GROQ_API_KEY,
                    temperature=0.1,
                    model_kwargs={"response_format": {"type": "json_object"}}
                )
                res = llm.invoke(messages)
                data = json.loads(self._clean_json_output(res.content))
                return data.get("nodes"), data.get("workflow_name"), self.config.GROQ_COMPILER_MODEL
            except Exception:
                pass

        return None, None, None

    def _default_node_mapping(self, node: SketchNode) -> Tuple[str, str, float, Dict[str, Any]]:
        """
        Deterministic fallback when LLM synthesis is unavailable.
        Uses the general-purpose N8N_NODE_CATALOG for type resolution.
        No hardcoded demo-specific parameters — returns minimal sensible defaults.
        """
        from sketchflow.agent.tools import N8N_NODE_CATALOG, NODE_INTENT_ALIASES
        import re as _re

        lbl = node.label.lower().strip()

        # Priority 1: Structural role detection (trigger/condition)
        if node.kind == "trigger" or "webhook" in lbl or "trigger" in lbl:
            return (
                node.label,
                "n8n-nodes-base.webhook",
                2.0,
                {"httpMethod": "POST", "path": node.id.replace("_", "-"), "responseMode": "onReceived"},
            )
        if node.kind == "condition" or node.shape == "diamond" or "?" in lbl or _re.search(r"\bif\b", lbl):
            return (
                node.label,
                "n8n-nodes-base.if",
                2.2,
                {"conditions": {"options": {"caseSensitive": True}, "conditions": [], "combinator": "and"}},
            )

        # Priority 2: Catalog keyword match
        for catalog_key, aliases in NODE_INTENT_ALIASES.items():
            for alias in aliases:
                if _re.search(r"\b" + _re.escape(alias) + r"\b", lbl):
                    entry = N8N_NODE_CATALOG.get(catalog_key)
                    if entry:
                        n8n_type, version, _cred = entry
                        return (node.label, n8n_type, version, {})

        # Priority 3: Universal fallback — Code node
        return (
            node.label,
            "n8n-nodes-base.code",
            2.0,
            {"language": "javaScript", "jsCode": f"// TODO: Configure '{node.label}'\nreturn $input.all();"},
        )

    def compile(
        self,
        graph: SketchGraph,
        workflow_name: Optional[str] = None,
        custom_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        docs_context: Optional[str] = None
    ) -> CompileWorkflowResponse:
        """Compiles any SketchGraph into a valid N8nWorkflowDTO with accurate canvas positions."""
        positions = self.compute_dag_positions(graph)
        nodes_dict = {n.id: n for n in graph.nodes}

        # Attempt LLM parameter synthesis
        synth_nodes, synth_name, model_used = self._synthesize_parameters_with_llm(
            graph, custom_parameters, docs_context=docs_context
        )

        n8n_nodes: List[N8nNodeDTO] = []
        id_to_name: Dict[str, str] = {}
        node_kind_map: Dict[str, str] = {}

        if synth_nodes:
            for item in synth_nodes:
                nid = item.get("node_id")
                if nid not in nodes_dict:
                    continue
                pos = positions.get(nid, [240, 300])
                name = item.get("n8n_name", nodes_dict[nid].label)
                id_to_name[nid] = name
                node_kind_map[nid] = nodes_dict[nid].kind

                params = dict(item.get("parameters", {}))
                creds = None

                # Apply user overrides from Human-in-the-Loop review (by name or node ID)
                if custom_parameters:
                    node_override = custom_parameters.get(name) or custom_parameters.get(nid) or {}
                    if isinstance(node_override, dict):
                        if "parameters" in node_override and isinstance(node_override["parameters"], dict):
                            params.update(node_override["parameters"])
                        elif not ("parameters" in node_override or "credentials" in node_override):
                            params.update(node_override)

                        if "credentials" in node_override and node_override["credentials"]:
                            creds = node_override["credentials"]

                n8n_nodes.append(N8nNodeDTO(
                    id=str(uuid.uuid4()),
                    name=name,
                    type=item.get("n8n_type", "n8n-nodes-base.code"),
                    typeVersion=item.get("type_version", 2.0),
                    position=pos,
                    parameters=params,
                    credentials=creds if creds else None
                ))
        else:
            # Fallback deterministic assembly
            for nid, node in nodes_dict.items():
                name, n_type, v, params = self._default_node_mapping(node)
                pos = positions.get(nid, [240, 300])
                id_to_name[nid] = name
                node_kind_map[nid] = node.kind

                creds = None
                if custom_parameters:
                    node_override = custom_parameters.get(name) or custom_parameters.get(nid) or {}
                    if isinstance(node_override, dict):
                        if "parameters" in node_override and isinstance(node_override["parameters"], dict):
                            params.update(node_override["parameters"])
                        elif not ("parameters" in node_override or "credentials" in node_override):
                            params.update(node_override)

                        if "credentials" in node_override and node_override["credentials"]:
                            creds = node_override["credentials"]

                n8n_nodes.append(N8nNodeDTO(
                    id=str(uuid.uuid4()),
                    name=name,
                    type=n_type,
                    typeVersion=v,
                    position=pos,
                    parameters=params,
                    credentials=creds if creds else None
                ))

        # Build n8n connections with true/false branch indexing
        connections: Dict[str, Dict[str, List[List[Dict[str, Any]]]]] = defaultdict(lambda: {"main": []})

        for edge in graph.edges:
            u, v = edge.from_id, edge.to_id
            if u not in id_to_name or v not in id_to_name:
                continue

            src_name = id_to_name[u]
            tgt_name = id_to_name[v]
            src_kind = node_kind_map.get(u, "action")
            lbl = str(edge.label or "").strip().lower()

            target_conn = {"node": tgt_name, "type": "main", "index": 0}

            if src_kind == "condition" or "if" in src_name.lower():
                is_false = (lbl in ["no", "false", "f", "0", "rejected"])
                branch_idx = 1 if is_false else 0
                while len(connections[src_name]["main"]) <= branch_idx:
                    connections[src_name]["main"].append([])
                connections[src_name]["main"][branch_idx].append(target_conn)
            else:
                if not connections[src_name]["main"]:
                    connections[src_name]["main"].append([])
                connections[src_name]["main"][0].append(target_conn)

        resolved_name = workflow_name or synth_name or "SketchFlow Generated Workflow"

        workflow_dto = N8nWorkflowDTO(
            name=resolved_name,
            nodes=n8n_nodes,
            connections=dict(connections),
            settings={"executionOrder": "v1"}
        )

        return CompileWorkflowResponse(
            workflow=workflow_dto,
            node_count=len(n8n_nodes),
            connection_count=len(graph.edges),
            synthesizer_model=model_used,
            layout_calculated=True
        )
