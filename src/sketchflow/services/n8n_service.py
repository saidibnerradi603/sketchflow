"""
n8n Service for interacting with self-hosted n8n instances via REST API and CLI.
Provides workflow deployment, activation, health monitoring, and live webhook verification.
"""

import os
import json
import subprocess
from typing import List, Dict, Any, Optional
import httpx

from sketchflow.core.config import settings, Settings
from sketchflow.schemas.workflow import N8nWorkflowDTO
from sketchflow.schemas.deployment import (
    DeployWorkflowResponse,
    TestWebhookResponse,
    WorkflowStatusResponse
)

class N8nService:
    """Client service for n8n REST API and Docker container lifecycle."""

    def __init__(self, config: Optional[Settings] = None):
        self.config = config or settings
        self.base_url = self.config.N8N_BASE_URL.rstrip("/")
        self.webhook_base_url = self.config.N8N_WEBHOOK_BASE_URL.rstrip("/")
        self.api_key = self.config.N8N_API_KEY or ""

    @property
    def headers(self) -> Dict[str, str]:
        return {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def check_health(self) -> bool:
        """Verifies connectivity to n8n server and valid authentication."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.get(f"{self.base_url}/workflows?limit=1", headers=self.headers)
                return res.status_code == 200
        except Exception:
            return False

    async def list_workflows(self, limit: int = 10) -> List[WorkflowStatusResponse]:
        """Lists active and inactive workflows from the n8n instance."""
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.get(f"{self.base_url}/workflows?limit={limit}", headers=self.headers)
            res.raise_for_status()
            data = res.json()
            items = data.get("data", [])
            return [
                WorkflowStatusResponse(
                    workflow_id=item.get("id"),
                    name=item.get("name", "Unnamed"),
                    active=item.get("active", False),
                    nodes_count=len(item.get("nodes", [])),
                    created_at=item.get("createdAt"),
                    updated_at=item.get("updatedAt")
                )
                for item in items
            ]

    def _activate_workflow_cli(self, workflow_id: str) -> bool:
        """Publishes the workflow in n8n engine using docker CLI."""
        container = self.config.N8N_DOCKER_CONTAINER_NAME
        try:
            res = subprocess.run(
                ["docker", "exec", container, "n8n", "publish:workflow", f"--id={workflow_id}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return res.returncode == 0
        except Exception:
            return False

    async def deploy_workflow(
        self,
        workflow: N8nWorkflowDTO,
        activate: bool = True
    ) -> DeployWorkflowResponse:
        """
        Deploys an authoritative n8n workflow payload to n8n.
        Optionally activates it and extracts listening webhook URLs.
        """
        payload = workflow.model_dump(exclude_none=True)
        async with httpx.AsyncClient(timeout=15.0) as client:
            res = await client.post(f"{self.base_url}/workflows", json=payload, headers=self.headers)
            res.raise_for_status()
            wf_data = res.json()
            wf_id = wf_data.get("id")

        is_active = False
        if activate and wf_id:
            # 1. Try modern n8n v2+ publish endpoint, then legacy activate endpoint, then PUT active
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    pub_res = await client.post(f"{self.base_url}/workflows/{wf_id}/publish", headers=self.headers)
                    if pub_res.status_code in (200, 201):
                        is_active = True
                    else:
                        act_res = await client.post(f"{self.base_url}/workflows/{wf_id}/activate", headers=self.headers)
                        if act_res.status_code in (200, 201):
                            is_active = True
                        else:
                            upd_res = await client.put(f"{self.base_url}/workflows/{wf_id}", json={"active": True}, headers=self.headers)
                            if upd_res.status_code in (200, 201):
                                is_active = True
            except Exception:
                pass

            # 2. Fallback to CLI if not active
            if not is_active:
                is_active = self._activate_workflow_cli(wf_id)

        # Extract any webhook URLs present in the workflow
        webhook_urls = []
        for node in workflow.nodes:
            if "webhook" in node.type.lower():
                path = node.parameters.get("path")
                if path:
                    webhook_urls.append(f"{self.webhook_base_url}/{path}")

        # Compute dynamic editor URL from configured base URL
        n8n_ui_host = self.base_url.replace("/api/v1", "").rstrip("/")
        editor_url = f"{n8n_ui_host}/workflow/{wf_id}" if wf_id else n8n_ui_host

        return DeployWorkflowResponse(
            workflow_id=wf_id or "unknown",
            workflow_name=workflow.name,
            active=is_active,
            webhook_urls=webhook_urls,
            editor_url=editor_url,
            message=f"Workflow '{workflow.name}' successfully deployed to n8n"
        )

    async def test_webhook(
        self,
        webhook_path: str,
        payload: Dict[str, Any],
        method: str = "POST"
    ) -> TestWebhookResponse:
        """Triggers an active webhook endpoint with test JSON payload."""
        url = f"{self.webhook_base_url}/{webhook_path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                if method.upper() == "POST":
                    res = await client.post(url, json=payload)
                else:
                    res = await client.get(url, params=payload)

                try:
                    res_body = res.json()
                except Exception:
                    res_body = res.text

                return TestWebhookResponse(
                    webhook_url=url,
                    status_code=res.status_code,
                    success=res.is_success,
                    response_data=res_body
                )
            except Exception as e:
                return TestWebhookResponse(
                    webhook_url=url,
                    status_code=500,
                    success=False,
                    response_data=str(e)
                )
