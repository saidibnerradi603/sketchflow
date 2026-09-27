"""
Agent Tools for SketchFlow.

General-purpose, agentic toolset for the LangGraph pipeline.
NO hardcoded demo schemas. NO static node dictionaries.
Uses a comprehensive keyword→type catalog covering 100+ n8n integrations,
with graceful fallback to universal nodes for anything unrecognized.
"""

import re
import httpx
from typing import Dict, Any, List, Optional
from sketchflow.schemas.diagram import SketchGraph, SketchNode, SketchEdge
from sketchflow.services.compiler_service import CompilerService

# ---------------------------------------------------------------------------
# Comprehensive n8n Node Type Catalog
# Maps lowercase keywords → (n8n_type, typeVersion, credential_type or None)
# This is NOT a 7-item demo dictionary. It covers the real n8n ecosystem.
# ---------------------------------------------------------------------------

N8N_NODE_CATALOG: Dict[str, tuple] = {
    # ── Core & Flow Control ──────────────────────────────────────────────
    "webhook":          ("n8n-nodes-base.webhook",          2.0,  None),
    "if":               ("n8n-nodes-base.if",               2.2,  None),
    "switch":           ("n8n-nodes-base.switch",           3.2,  None),
    "code":             ("n8n-nodes-base.code",             2.0,  None),
    "set":              ("n8n-nodes-base.set",              3.4,  None),
    "merge":            ("n8n-nodes-base.merge",            3.0,  None),
    "filter":           ("n8n-nodes-base.filter",           2.2,  None),
    "sort":             ("n8n-nodes-base.sort",             1.0,  None),
    "limit":            ("n8n-nodes-base.limit",            1.0,  None),
    "dedup":            ("n8n-nodes-base.removeDuplicates", 1.0,  None),
    "batch":            ("n8n-nodes-base.splitInBatches",   3.0,  None),
    "aggregate":        ("n8n-nodes-base.aggregate",        1.0,  None),
    "wait":             ("n8n-nodes-base.wait",             1.1,  None),
    "noop":             ("n8n-nodes-base.noOp",             1.0,  None),
    "httprequest":      ("n8n-nodes-base.httpRequest",      4.2,  None),
    "respond":          ("n8n-nodes-base.respondToWebhook", 1.1,  None),
    "schedule":         ("n8n-nodes-base.scheduleTrigger",  1.2,  None),
    "manual":           ("n8n-nodes-base.manualTrigger",    1.0,  None),
    "errortrigger":     ("n8n-nodes-base.errorTrigger",     1.0,  None),
    "subworkflow":      ("n8n-nodes-base.executeWorkflow",  1.0,  None),
    "datetime":         ("n8n-nodes-base.dateTime",         2.0,  None),
    "crypto":           ("n8n-nodes-base.crypto",           1.0,  None),
    "xml":              ("n8n-nodes-base.xml",              1.0,  None),
    "html":             ("n8n-nodes-base.html",             1.0,  None),
    "markdown":         ("n8n-nodes-base.markdown",         1.0,  None),
    "converttofile":    ("n8n-nodes-base.convertToFile",    1.1,  None),
    "extractfromfile":  ("n8n-nodes-base.extractFromFile",  1.0,  None),
    "readpdf":          ("n8n-nodes-base.readPdf",          1.0,  None),
    "spreadsheet":      ("n8n-nodes-base.spreadsheetFile",  2.0,  None),
    "compression":      ("n8n-nodes-base.compression",      1.0,  None),
    "itemlists":        ("n8n-nodes-base.itemLists",        3.1,  None),
    # ── Communication & Messaging ────────────────────────────────────────
    "slack":            ("n8n-nodes-base.slack",            2.2,  "slackApi"),
    "discord":          ("n8n-nodes-base.discord",          2.1,  "discordApi"),
    "telegram":         ("n8n-nodes-base.telegram",         1.2,  "telegramApi"),
    "whatsapp":         ("n8n-nodes-base.whatsApp",         1.0,  "whatsAppApi"),
    "teams":            ("n8n-nodes-base.microsoftTeams",   2.0,  "microsoftTeamsOAuth2Api"),
    "email":            ("n8n-nodes-base.emailSend",        2.2,  "smtp"),
    "imap":             ("n8n-nodes-base.emailReadImap",    2.1,  "imap"),
    "gmail":            ("n8n-nodes-base.gmail",            2.1,  "gmailOAuth2"),
    "outlook":          ("n8n-nodes-base.microsoftOutlook", 2.0,  "microsoftOutlookOAuth2Api"),
    "twilio":           ("n8n-nodes-base.twilio",           1.0,  "twilioApi"),
    "sendgrid":         ("n8n-nodes-base.sendGrid",         1.0,  "sendGridApi"),
    "mailchimp":        ("n8n-nodes-base.mailchimp",        1.0,  "mailchimpApi"),
    # ── Databases & Data Stores ──────────────────────────────────────────
    "postgres":         ("n8n-nodes-base.postgres",         2.5,  "postgres"),
    "mysql":            ("n8n-nodes-base.mySql",            2.4,  "mySql"),
    "mongodb":          ("n8n-nodes-base.mongoDb",          1.1,  "mongoDb"),
    "redis":            ("n8n-nodes-base.redis",            1.0,  "redis"),
    "googlesheets":     ("n8n-nodes-base.googleSheets",     4.5,  "googleSheetsOAuth2Api"),
    "airtable":         ("n8n-nodes-base.airtable",         2.1,  "airtableTokenApi"),
    "notion":           ("n8n-nodes-base.notion",           2.2,  "notionApi"),
    "supabase":         ("n8n-nodes-base.supabase",         1.0,  "supabaseApi"),
    "bigquery":         ("n8n-nodes-base.googleBigQuery",   2.0,  "googleBigQueryOAuth2Api"),
    "elasticsearch":    ("n8n-nodes-base.elasticsearch",    1.0,  "elasticsearchApi"),
    "mssql":            ("n8n-nodes-base.microsoftSql",     1.0,  "microsoftSql"),
    "dynamodb":         ("n8n-nodes-base.dynamoDb",         1.0,  "aws"),
    "firestore":        ("n8n-nodes-base.googleFirebaseCloudFirestore", 1.0, "googleFirebaseCloudFirestoreOAuth2Api"),
    # ── CRM & Business Tools ────────────────────────────────────────────
    "hubspot":          ("n8n-nodes-base.hubspot",          2.1,  "hubspotApi"),
    "salesforce":       ("n8n-nodes-base.salesforce",       1.0,  "salesforceOAuth2Api"),
    "pipedrive":        ("n8n-nodes-base.pipedrive",        1.0,  "pipedriveApi"),
    "freshdesk":        ("n8n-nodes-base.freshdesk",        1.0,  "freshdeskApi"),
    "zendesk":          ("n8n-nodes-base.zendesk",          1.0,  "zendeskApi"),
    "intercom":         ("n8n-nodes-base.intercom",         1.0,  "intercomApi"),
    "calendly":         ("n8n-nodes-base.calendly",         1.0,  "calendlyApi"),
    "asana":            ("n8n-nodes-base.asana",            1.0,  "asanaApi"),
    "trello":           ("n8n-nodes-base.trello",           1.0,  "trelloApi"),
    "clickup":          ("n8n-nodes-base.clickUp",          1.0,  "clickUpApi"),
    "todoist":          ("n8n-nodes-base.todoist",          2.0,  "todoistApi"),
    "monday":           ("n8n-nodes-base.mondayCom",        1.0,  "mondayComApi"),
    "googlecalendar":   ("n8n-nodes-base.googleCalendar",   1.0,  "googleCalendarOAuth2Api"),
    # ── Payment & E-Commerce ────────────────────────────────────────────
    "stripe":           ("n8n-nodes-base.stripe",           2.0,  "stripeApi"),
    "shopify":          ("n8n-nodes-base.shopify",          1.0,  "shopifyApi"),
    "woocommerce":      ("n8n-nodes-base.wooCommerce",      1.0,  "wooCommerceApi"),
    "paypal":           ("n8n-nodes-base.payPal",           1.0,  "payPalApi"),
    # ── Developer & DevOps ──────────────────────────────────────────────
    "github":           ("n8n-nodes-base.github",           1.0,  "githubApi"),
    "gitlab":           ("n8n-nodes-base.gitlab",           1.0,  "gitlabApi"),
    "jira":             ("n8n-nodes-base.jira",             1.0,  "jiraSoftwareCloudApi"),
    "linear":           ("n8n-nodes-base.linear",           1.0,  "linearApi"),
    "s3":               ("n8n-nodes-base.awsS3",            1.0,  "aws"),
    "lambda":           ("n8n-nodes-base.awsLambda",        1.0,  "aws"),
    "sns":              ("n8n-nodes-base.awsSns",            1.0,  "aws"),
    "sqs":              ("n8n-nodes-base.awsSqs",            1.0,  "aws"),
    "gcs":              ("n8n-nodes-base.googleCloudStorage",1.0,  "googleCloudStorageOAuth2Api"),
    # ── AI & ML ─────────────────────────────────────────────────────────
    "openai":           ("@n8n/n8n-nodes-langchain.openAi", 1.8,  "openAiApi"),
    "aiagent":          ("@n8n/n8n-nodes-langchain.agent",  1.7,  "openAiApi"),
    # ── Analytics & Monitoring ──────────────────────────────────────────
    "googleanalytics":  ("n8n-nodes-base.googleAnalytics",  2.0,  "googleAnalyticsOAuth2"),
    "sentry":           ("n8n-nodes-base.sentry",           1.0,  "sentryIoApi"),
    # ── Social Media ────────────────────────────────────────────────────
    "twitter":          ("n8n-nodes-base.twitter",          2.0,  "twitterOAuth2Api"),
    "facebook":         ("n8n-nodes-base.facebookGraphApi", 1.0,  "facebookGraphApi"),
    # ── Cloud & Storage ─────────────────────────────────────────────────
    "googledrive":      ("n8n-nodes-base.googleDrive",      3.0,  "googleDriveOAuth2Api"),
    "dropbox":          ("n8n-nodes-base.dropbox",          1.0,  "dropboxApi"),
    "onedrive":         ("n8n-nodes-base.microsoftOneDrive", 1.0, "microsoftOneDriveOAuth2Api"),
    "box":              ("n8n-nodes-base.box",              1.0,  "boxOAuth2Api"),
    # ── Forms & Surveys ─────────────────────────────────────────────────
    "typeform":         ("n8n-nodes-base.typeform",         1.0,  "typeformApi"),
    "googleforms":      ("n8n-nodes-base.googleForms",      1.0,  "googleFormsOAuth2Api"),
}

# ---------------------------------------------------------------------------
# Keyword aliases → canonical catalog key
# Handles natural language variety (e.g. "database" → "postgres",
# "notify" → "slack", "spreadsheet" → "googlesheets")
# ---------------------------------------------------------------------------

NODE_INTENT_ALIASES: Dict[str, List[str]] = {
    # Core
    "webhook":      ["webhook", "trigger", "intake", "incoming", "start", "listener", "receive", "endpoint"],
    "if":           ["if", "condition", "decision", "check", "branch", "gate", "router", "conditional"],
    "switch":       ["switch", "route", "multiplex", "case"],
    "code":         ["code", "script", "transform", "javascript", "python", "custom", "function", "compute"],
    "set":          ["set", "assign", "rename", "map", "setfield"],
    "merge":        ["merge", "combine", "join", "union", "concat"],
    "filter":       ["filter", "where", "exclude", "include", "sieve"],
    "httprequest":  ["http", "api", "fetch", "rest", "request", "curl", "endpoint_call"],
    "respond":      ["respond", "reply", "response", "answer"],
    "schedule":     ["schedule", "cron", "interval", "timer", "recurring", "periodic"],
    "wait":         ["wait", "delay", "pause", "sleep"],
    # Communication
    "slack":        ["slack", "alert", "notify", "notification", "message", "chat"],
    "discord":      ["discord"],
    "telegram":     ["telegram", "tg", "bot"],
    "whatsapp":     ["whatsapp", "wa"],
    "teams":        ["teams", "microsoftteams"],
    "email":        ["email", "mail", "smtp", "send_email", "sendemail"],
    "gmail":        ["gmail"],
    "twilio":       ["twilio", "sms", "text_message"],
    # Databases
    "postgres":     ["postgres", "postgresql", "sql", "database", "db", "query", "pg"],
    "mysql":        ["mysql", "mariadb"],
    "mongodb":      ["mongodb", "mongo", "nosql"],
    "redis":        ["redis", "cache"],
    "googlesheets": ["sheets", "spreadsheet", "googlesheet", "google_sheets", "gsheet"],
    "airtable":     ["airtable"],
    "notion":       ["notion"],
    "supabase":     ["supabase"],
    "firestore":    ["firestore", "firebase"],
    # CRM
    "hubspot":      ["hubspot", "crm"],
    "salesforce":   ["salesforce", "sfdc"],
    "jira":         ["jira", "ticket", "issue"],
    "asana":        ["asana", "task"],
    "trello":       ["trello", "board", "card"],
    "linear":       ["linear"],
    # Payment
    "stripe":       ["stripe", "payment", "charge", "invoice"],
    "shopify":      ["shopify", "ecommerce", "store", "order"],
    # Dev
    "github":       ["github", "repo", "pr", "pull_request"],
    "gitlab":       ["gitlab"],
    # AI
    "openai":       ["openai", "gpt", "chatgpt", "llm", "ai"],
    # Storage
    "googledrive":  ["gdrive", "googledrive", "drive"],
    "s3":           ["s3", "aws_s3", "bucket"],
    "dropbox":      ["dropbox"],
}


# ---------------------------------------------------------------------------
# Tool 1 — General-Purpose Node Type Resolution
# ---------------------------------------------------------------------------

def inspect_node_schema(query: str) -> Dict[str, Any]:
    """
    Agent Tool: Resolves natural-language node intent into the best-matching
    n8n node type from a catalog of 100+ integrations.

    This is a HINT tool — it provides a best-guess type suggestion.
    The authoritative node configuration is synthesized by the LLM compiler.

    Returns:
        dict with keys: found (bool), n8n_type (str), type_version (float),
        credential_type (str|None), matched_keyword (str)
    """
    clean = query.lower().strip()

    # Phase 1: Try direct keyword match against aliases
    for catalog_key, aliases in NODE_INTENT_ALIASES.items():
        for alias in aliases:
            if re.search(r"\b" + re.escape(alias) + r"\b", clean):
                entry = N8N_NODE_CATALOG.get(catalog_key)
                if entry:
                    n8n_type, version, cred = entry
                    return {
                        "found": True,
                        "n8n_type": n8n_type,
                        "type_version": version,
                        "credential_type": cred,
                        "matched_keyword": catalog_key,
                    }

    # Phase 2: Try direct catalog key match (handles exact service names)
    for key, entry in N8N_NODE_CATALOG.items():
        if key in clean:
            n8n_type, version, cred = entry
            return {
                "found": True,
                "n8n_type": n8n_type,
                "type_version": version,
                "credential_type": cred,
                "matched_keyword": key,
            }

    # Phase 3: Graceful fallback — let the LLM handle it
    return {
        "found": False,
        "n8n_type": "n8n-nodes-base.httpRequest",
        "type_version": 4.2,
        "credential_type": None,
        "matched_keyword": None,
        "message": (
            f"No catalog match for '{query}'. Suggested fallback: httpRequest. "
            f"The LLM compiler will synthesize the correct type and parameters."
        ),
    }


# ---------------------------------------------------------------------------
# Tool 2 — Dynamic n8n Documentation Search
# ---------------------------------------------------------------------------

_LLMS_TXT_INDEX: Optional[List[str]] = None

async def search_n8n_docs(query: str) -> str:
    """
    Agent Tool: Queries official n8n documentation (docs.n8n.io) dynamically.

    Fetches official Markdown-formatted docs directly from n8n's llms.txt index
    and .md documentation endpoints. Falls back to a comprehensive expression
    syntax reference if offline or unreachable.
    """
    global _LLMS_TXT_INDEX
    clean_query = query.lower().strip()

    candidate_urls: List[str] = []

    # Priority 1: Expression syntax & data transformation
    if any(k in clean_query for k in ["expression", "syntax", "$json", "item", "variable"]):
        candidate_urls.append("https://docs.n8n.io/build/work-with-data/transform-data/expression-reference.md")
        candidate_urls.append("https://docs.n8n.io/build/work-with-data/transform-data/expressions-for-data-transformation.md")

    # Priority 2: Direct node catalog match to core or app markdown docs
    for key, entry in N8N_NODE_CATALOG.items():
        if key in clean_query:
            n8n_type = entry[0]
            if n8n_type.startswith("n8n-nodes-base."):
                candidate_urls.append(f"https://docs.n8n.io/integrations/builtin/core-nodes/{n8n_type}.md")
                candidate_urls.append(f"https://docs.n8n.io/integrations/builtin/app-nodes/{n8n_type}.md")
            break

    # Priority 3: Common topic routes in n8n docs
    if any(k in clean_query for k in ["if", "condition", "branch", "switch"]):
        candidate_urls.append("https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if.md")
        candidate_urls.append("https://docs.n8n.io/build/flow-logic/branch-workflow.md")

    headers = {"User-Agent": "SketchFlowAgent/1.0 (Linux; x86_64)"}

    # Attempt fetching candidate Markdown files directly
    async with httpx.AsyncClient(timeout=5.0, follow_redirects=True, headers=headers) as client:
        for url in candidate_urls:
            try:
                res = await client.get(url)
                if res.status_code == 200 and len(res.text) > 100:
                    lines = [l for l in res.text.split("\n") if not l.startswith(">")]
                    clean_md = "\n".join(lines).strip()
                    if clean_md and "page not found" not in clean_md.lower() and "does not exist" not in clean_md.lower():
                        return clean_md[:5000]
            except Exception:
                continue

        # Dynamic search via llms.txt index
        try:
            if _LLMS_TXT_INDEX is None:
                r = await client.get("https://docs.n8n.io/llms.txt")
                if r.status_code == 200:
                    _LLMS_TXT_INDEX = r.text.split("\n")
                else:
                    _LLMS_TXT_INDEX = []

            keywords = [w for w in re.split(r"[^a-zA-Z0-9]+", clean_query) if len(w) > 2]
            for line in _LLMS_TXT_INDEX:
                if any(w in line.lower() for w in keywords):
                    match = re.search(r"\((https://docs\.n8n\.io/[^\)]+\.md)\)", line)
                    if match:
                        doc_url = match.group(1)
                        res = await client.get(doc_url)
                        if res.status_code == 200:
                            lines = [l for l in res.text.split("\n") if not l.startswith(">")]
                            clean_md = "\n".join(lines).strip()
                            if clean_md:
                                return clean_md[:5000]
        except Exception:
            pass

    # Final fallback: return comprehensive built-in reference
    return _EXPRESSION_REFERENCE


# Built-in expression syntax reference (returned when docs fetch fails)
_EXPRESSION_REFERENCE = """\
# n8n Expression Syntax Quick Reference

## Data Access
- Current item:    {{ $json.fieldName }}
- Nested field:    {{ $json.body.user.email }}
- Named node:      {{ $('Node Name').item.json.field }}
- All items:       {{ $('Node Name').all() }}

## Webhook Specific
- Full body:       {{ $json.body }}
- Headers:         {{ $json.headers }}
- Query params:    {{ $json.query }}
- URL path:        {{ $json.params }}

## Operators
- Ternary:         {{ $json.x > 10 ? 'big' : 'small' }}
- Fallback:        {{ $json.name || 'default' }}
- Template:        Hello {{ $json.body.name }}!

## Built-in Variables
- {{ $now }}        — Current DateTime
- {{ $today }}      — Today at midnight
- {{ $itemIndex }}  — Current item index (0-based)
- {{ $runIndex }}   — Execution run count
- {{ $workflow.id }}    — Workflow ID
- {{ $workflow.name }}  — Workflow name
- {{ $execution.id }}   — Execution ID

## IF Node Conditions
- main[0] = True branch (condition met)
- main[1] = False branch (condition not met)
"""


# ---------------------------------------------------------------------------
# Tool 3 — Deterministic DAG Layout Calculator
# ---------------------------------------------------------------------------

def calculate_dag_layout(
    nodes: List[Dict[str, Any]],
    edges: List[Dict[str, Any]],
) -> Dict[str, List[int]]:
    """
    Agent Tool: Computes topological non-overlapping [x, y] coordinates
    for all nodes in the sketch graph.  Pure algorithmic — no AI involved.
    """
    snodes = [SketchNode(**n) for n in nodes]
    sedges = [SketchEdge(**e) for e in edges]
    graph = SketchGraph(nodes=snodes, edges=sedges)
    compiler = CompilerService()
    return compiler.compute_dag_positions(graph)


# ---------------------------------------------------------------------------
# Tool 4 — Workflow Structure Linter
# ---------------------------------------------------------------------------

def validate_n8n_workflow(workflow_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agent Tool: Rule-based linter that validates n8n workflow structure
    before deployment. Checks for common structural issues that would
    cause n8n to reject the payload.
    """
    errors: List[str] = []
    warnings: List[str] = []
    nodes = workflow_dict.get("nodes", [])
    connections = workflow_dict.get("connections", {})

    # ── Check: Workflow has nodes ──
    if not nodes:
        errors.append("Workflow has no nodes.")
        return {
            "valid": False,
            "errors": errors,
            "warnings": warnings,
            "total_nodes": 0,
            "total_connections": 0,
        }

    # ── Check: Node names and types ──
    node_names: set = set()
    has_trigger = False
    for n in nodes:
        name = n.get("name")
        ntype = n.get("type", "")

        if not name:
            errors.append("Found node without a 'name' field.")
        elif name in node_names:
            errors.append(f"Duplicate node name: '{name}'.")
        node_names.add(name)

        if not ntype:
            errors.append(f"Node '{name}' has no 'type' field.")
        elif not (ntype.startswith("n8n-nodes-base.") or ntype.startswith("@n8n/")):
            warnings.append(
                f"Node '{name}' has unusual type '{ntype}' — "
                f"expected prefix 'n8n-nodes-base.' or '@n8n/'."
            )

        if "webhook" in ntype.lower() or "trigger" in ntype.lower():
            has_trigger = True

        # Check typeVersion is set
        if "typeVersion" not in n:
            warnings.append(f"Node '{name}' missing 'typeVersion'.")

        # Check position is set
        if "position" not in n:
            warnings.append(f"Node '{name}' missing 'position'.")

    # ── Check: Has at least one trigger ──
    if not has_trigger:
        errors.append(
            "Workflow has no trigger/entrypoint node (webhook, scheduleTrigger, etc.)."
        )

    # ── Check: Connections reference valid nodes ──
    for source_name, conn_data in connections.items():
        if source_name not in node_names:
            errors.append(
                f"Connection source '{source_name}' is not a known node."
            )
        if isinstance(conn_data, dict):
            for port, targets in conn_data.items():
                if isinstance(targets, list):
                    for target_list in targets:
                        if isinstance(target_list, list):
                            for target in target_list:
                                target_name = target.get("node", "")
                                if target_name and target_name not in node_names:
                                    errors.append(
                                        f"Connection target '{target_name}' "
                                        f"(from '{source_name}') is not a known node."
                                    )

    # ── Check: executionOrder setting ──
    settings = workflow_dict.get("settings", {})
    if settings.get("executionOrder") != "v1":
        warnings.append("Missing or non-v1 executionOrder in settings.")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "total_nodes": len(nodes),
        "total_connections": len(connections),
    }
