"""
Experiment 03: Dynamic n8n Node Schema Inspector Skill
Tests the agent's ability to look up exact n8n node types, typeVersion,
and required parameter schemas dynamically on the fly rather than guessing.
"""

import os
import json

# In-memory fast schema registry for core nodes (mirrors n8n official node definitions)
LOCAL_NODE_REGISTRY = {
    "webhook": {
        "n8n_type": "n8n-nodes-base.webhook",
        "typeVersion": 2,
        "default_parameters": {
            "httpMethod": "POST",
            "path": "{slug}",
            "responseMode": "onReceived"
        },
        "description": "Trigger workflow when HTTP POST/GET request is received"
    },
    "if": {
        "n8n_type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "default_parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
                "conditions": [
                    {
                        "id": "cond_1",
                        "leftValue": "={{ $json.body.is_vip }}",
                        "rightValue": True,
                        "operator": {"type": "boolean", "operation": "equals"}
                    }
                ],
                "combinator": "and"
            }
        },
        "description": "Route data conditionally into True (main[0]) or False (main[1]) branches"
    },
    "slack": {
        "n8n_type": "n8n-nodes-base.slack",
        "typeVersion": 2.2,
        "default_parameters": {
            "select": "channel",
            "channelId": "alerts",
            "text": "={{ $json.body.message || 'Notification from SketchFlow' }}"
        },
        "description": "Send a message to a Slack channel"
    },
    "googlesheets": {
        "n8n_type": "n8n-nodes-base.googleSheets",
        "typeVersion": 4.5,
        "default_parameters": {
            "operation": "append",
            "sheetName": "Sheet1"
        },
        "description": "Append row to a Google Spreadsheet"
    },
    "code": {
        "n8n_type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "default_parameters": {
            "language": "javaScript",
            "jsCode": "return $input.all();"
        },
        "description": "Run custom JavaScript/Python data transformation"
    }
}

def lookup_node_schema(intent_name: str) -> dict:
    """
    Simulates the Agent tool: resolves a natural language label
    to an authoritative n8n node configuration.
    """
    cleaned = intent_name.lower().replace(" ", "").replace("-", "").replace("_", "")
    
    # Check direct match or substring in local registry
    for key, spec in LOCAL_NODE_REGISTRY.items():
        if key in cleaned or cleaned in key:
            return {
                "found": True,
                "source": "local_registry",
                "spec": spec
            }
            
    # If not found in local core, we would query n8n documentation API / MCP:
    # URL: https://docs.n8n.io/integrations/builtin/core-nodes/
    return {
        "found": False,
        "source": "remote_fallback",
        "error": f"Node schema for '{intent_name}' requires dynamic documentation retrieval."
    }

def test_dynamic_lookup():
    print("="*60)
    print("Testing Dynamic n8n Node Schema Inspector Skill")
    print("="*60)
    
    sample_intents = [
        "New Lead Webhook",
        "Is VIP customer?",
        "Post Slack alert",
        "Save to Google Sheets",
        "Transform JS code",
        "Unknown Custom Service"
    ]
    
    for intent in sample_intents:
        res = lookup_node_schema(intent)
        if res["found"]:
            spec = res["spec"]
            print(f"\n[FOUND] Intent: '{intent}'")
            print(f"  → Node Type:   {spec['n8n_type']}")
            print(f"  → Version:     {spec['typeVersion']}")
            print(f"  → Parameters:  {json.dumps(spec['default_parameters'], indent=4)}")
        else:
            print(f"\n[UNRESOLVED] Intent: '{intent}' → Triggering remote MCP search...")

if __name__ == "__main__":
    test_dynamic_lookup()
