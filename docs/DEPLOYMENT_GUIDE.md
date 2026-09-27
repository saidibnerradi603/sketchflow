# Production Deployment Guide: Railway (n8n + Backend) & Netlify (UI)

This guide documents the end-to-end production deployment of **SketchFlow** across **Railway** (hosting n8n and the FastAPI LangGraph backend) and **Netlify** (hosting the React Excalidraw frontend studio).

---

## 1. Production Architecture Overview

```
                      ┌──────────────────────────────────────────┐
                      │            User Browser / Client         │
                      └─────────────────┬────────────────────────┘
                                        │
           ┌────────────────────────────┴───────────────────────────┐
           │ HTTPS (Static UI Bundle)                               │ HTTPS / SSE Stream
           ▼                                                        ▼
┌─────────────────────────┐                            ┌─────────────────────────┐
│     NETLIFY (Edge)      │                            │    RAILWAY (Backend)    │
│  sketchflow.netlify.app │                            │  sketchflow-api.railway │
│                         │                            │                         │
│  • React 18 + Vite SPA  │                            │  • FastAPI Application  │
│  • Excalidraw Canvas    │                            │  • LangGraph HITL Agent │
│  • agentStream.js       ├─ VITE_API_BASE_URL (CORS) ─►  • Vision & DAG Compiler│
└─────────────────────────┘                            └────────────┬────────────┘
                                                                    │
                                       Private / Public HTTPS REST  │ (X-N8N-API-KEY)
                                       + Webhook Verifications      │
                                                                    ▼
                                                       ┌─────────────────────────┐
                                                       │     RAILWAY (n8n Engine)│
                                                       │    n8n.up.railway.app   │
                                                       │                         │
                                                       │  • Official n8n Docker  │
                                                       │  • Persistent SQLite Vol│
                                                       │  • Active Webhook Slugs │
                                                       └─────────────────────────┘
```

### Why this architecture works:
1. **Zero SSE Proxy Buffering**: The browser opens Server-Sent Events (SSE) connections **directly** to the Railway backend domain (`VITE_API_BASE_URL`), bypassing Netlify's 26-second proxy timeout and response buffering.
2. **CORS Pre-Configured**: FastAPI's CORS middleware allows all incoming requests from Netlify.
3. **Decoupled Workflows**: n8n runs independently with persistent SQLite storage; restarting the SketchFlow backend does not disrupt running n8n automation triggers.

---

## 2. Phase 1: Deploy & Configure n8n on Railway

### 2.1 Provision n8n from Railway Template
1. Open your **Railway Dashboard**.
2. Click **+ New** $\rightarrow$ **Template** $\rightarrow$ Search for **n8n**.
3. Select the official n8n template (uses `n8nio/n8n` with an SQLite volume mounted to `/home/node/.n8n`).
4. Click **Deploy Template**.

### 2.2 Configure n8n Environment Variables (CRITICAL)
In Railway, navigate to your newly created **n8n Service** $\rightarrow$ **Variables** tab, and verify/add the following:

| Variable | Recommended Value | Why It Is Mandatory |
| :--- | :--- | :--- |
| `N8N_PORT` | `${{PORT}}` | Binds n8n to Railway's dynamic container port. |
| `N8N_PROTOCOL` | `https` | Ensures generated workflow URLs use TLS. |
| `N8N_PROXY_HOPS` | `1` | Informs n8n to trust Railway's reverse proxy SSL termination. |
| `N8N_WEBHOOK_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | **CRITICAL**: Tells n8n its external URL. Without this, webhook triggers default to `http://localhost:5678`! |
| `N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS` | `true` | Prevents container permission warnings. |

> [!IMPORTANT]
> Ensure a **Public Domain** is generated under **Service Settings** $\rightarrow$ **Networking** $\rightarrow$ **Generate Domain** (e.g. `n8n-production-xxxx.up.railway.app`).

### 2.3 Create Public API Key in n8n
1. Open your n8n public URL in the browser: `https://<your-n8n-subdomain>.up.railway.app`.
2. Complete the initial admin setup (create owner account email & password).
3. In the lower-left sidebar, click **Settings (Gear Icon)** $\rightarrow$ **Public API**.
4. Click **Create API Key**.
5. Label it `sketchflow-backend` and copy the generated key (starts with `n8n_api_...`).
   *Save this key—you will pass it into the SketchFlow backend.*

---

## 3. Phase 2: Deploy SketchFlow Backend on Railway

### 3.1 Create Backend Service
1. In the same Railway Project (or a new one), click **+ New** $\rightarrow$ **GitHub Repo**.
2. Select your `sketchflow` repository.
3. Railway automatically detects [`Dockerfile`](file:///home/ubuntu/Desktop/SketchFlow/Dockerfile) in the root and builds the Python 3.11 environment.

### 3.2 Configure Backend Environment Variables
Go to your **SketchFlow Backend Service** $\rightarrow$ **Variables** tab and set:

```bash
# ==============================================================================
# AI Multimodal Vision & Compiler Providers
# ==============================================================================
DEFAULT_PROVIDER="nvidia"
NVIDIA_API_KEY="nvapi-xxxxxxxxxxxxxxxxxxxxxxxx"
NVIDIA_VISION_MODEL="meta/llama-3.2-90b-vision-instruct"
NVIDIA_COMPILER_MODEL="nvidia/nemotron-3-ultra-550b-a55b"

# Optional fallback provider
GROQ_API_KEY="gsk_xxxxxxxxxxxxxxxxxxxxxxxx"
GROQ_VISION_MODEL="llama-3.2-90b-vision-preview"
GROQ_COMPILER_MODEL="openai/gpt-oss-120b"

# ==============================================================================
# Target n8n Instance Connection (CRITICAL)
# ==============================================================================
# Notice: N8N_BASE_URL MUST include '/api/v1' at the end!
N8N_BASE_URL="https://n8n-production-xxxx.up.railway.app/api/v1"
N8N_API_KEY="n8n_api_xxxxxxxxxxxxxxxxxxxxxxxx"

# Webhook Base URL for external triggers and test events
N8N_WEBHOOK_BASE_URL="https://n8n-production-xxxx.up.railway.app/webhook"

# ==============================================================================
# General Settings
# ==============================================================================
PROJECT_NAME="SketchFlow"
DEBUG="false"
```

> [!TIP]
> If n8n and SketchFlow Backend are in the **same Railway project**, you can optionally use Railway Private Networking for `N8N_BASE_URL`:
> `N8N_BASE_URL="http://n8n.railway.internal:5678/api/v1"`
> *(However, `N8N_WEBHOOK_BASE_URL` MUST remain the public HTTPS URL so external clients and test webhooks can reach it).*

### 3.3 Verify Backend Health
Under **Service Settings** $\rightarrow$ **Networking**, click **Generate Domain** (e.g. `sketchflow-api-production.up.railway.app`).

Verify backend connectivity in your terminal or browser:
```bash
curl -i https://sketchflow-api-production.up.railway.app/api/v1/health
```
Expected response:
```json
{"status":"healthy","project":"SketchFlow","n8n_connected":true}
```
If `"n8n_connected": false`, double check your `N8N_BASE_URL` (ensure it ends in `/api/v1`) and your `N8N_API_KEY`.

---

## 4. Phase 3: Deploy React Studio UI on Netlify

### 4.1 Zero-Config Deploy with `netlify.toml`
The repository includes a root [`netlify.toml`](file:///home/ubuntu/Desktop/SketchFlow/netlify.toml) configured with:
- Base directory: `src/sketchflow/ui`
- Build command: `npm run build`
- Publish directory: `dist`

1. Log into **Netlify** $\rightarrow$ **Add new site** $\rightarrow$ **Import an existing project**.
2. Connect your GitHub account and select your `sketchflow` repository.
3. Netlify will auto-populate the build settings from `netlify.toml`.

### 4.2 Configure Frontend Environment Variable
Before clicking Deploy, click **Add environment variables** (or go to **Site configuration** $\rightarrow$ **Environment variables**):

| Key | Value | Description |
| :--- | :--- | :--- |
| `VITE_API_BASE_URL` | `https://sketchflow-api-production.up.railway.app` | The public Railway URL of your backend. |

> [!IMPORTANT]
> In Vite, all client environment variables must start with `VITE_`.
> [`src/sketchflow/ui/src/services/agentStream.js`](file:///home/ubuntu/Desktop/SketchFlow/src/sketchflow/ui/src/services/agentStream.js) reads `import.meta.env.VITE_API_BASE_URL` at runtime.

4. Click **Deploy site**.
5. Once complete, your studio is live at `https://<site-name>.netlify.app`.

---

## 5. End-to-End Verification Checklist

Perform this 5-step test once all services are active:

1. **System Health Pill**:
   - Open `https://<site-name>.netlify.app`.
   - Inspect the top header. The health pill should display **System Online** (verified via `GET /api/v1/health`).
2. **Diagram Perception**:
   - Draw a simple pipeline in the Excalidraw canvas (e.g., `[Webhook] -> [Code] -> [Slack]`) or upload a sample architecture diagram.
   - Click **Run SketchFlow Agent**.
3. **SSE Telemetry Streaming**:
   - Confirm the right-hand **Agent Telemetry** terminal displays live log events (`perceive` $\rightarrow$ `compile` $\rightarrow$ `human_review`).
4. **HITL Review Modal**:
   - The UI will pause and pop up the **Review & Refine Workflow** modal.
   - Verify the node cards, inspect parameter expressions, optionally adjust values, and click **Approve & Deploy**.
5. **Live n8n Deployment & Verification**:
   - The agent transitions to `deploy` and triggers the n8n REST API.
   - Open your n8n Railway tab: confirm the workflow appears and has its toggle turned to **Active**.
   - On the Netlify UI **Deployment Card**, click **Test Webhook**. Verify that n8n receives the test event and records an execution run.

---

## 6. Troubleshooting & Gotchas

### Issue 1: `n8n_connected: false` in `/api/v1/health`
- **Cause**: `N8N_BASE_URL` is missing the `/api/v1` path suffix.
- **Fix**: Ensure `N8N_BASE_URL="https://n8n-production-xxxx.up.railway.app/api/v1"` (do not omit `/api/v1`).
- **Cause 2**: Invalid or expired API key. Generate a fresh key under n8n **Settings $\rightarrow$ Public API**.

### Issue 2: Webhooks show `http://localhost:5678/webhook/...` in n8n
- **Cause**: `N8N_WEBHOOK_URL` is not set on the n8n Railway service.
- **Fix**: Set `N8N_WEBHOOK_URL=https://n8n-production-xxxx.up.railway.app` on n8n's environment variables and restart the service.

### Issue 3: SSE Stream disconnected prematurely
- **Cause**: Browser tried connecting through a proxy rewrite instead of direct origin.
- **Fix**: Verify `VITE_API_BASE_URL` is set in Netlify site settings and points directly to your Railway backend URL.

### Issue 4: CORS blocked on browser requests
- **Cause**: Custom headers or domain mismatches.
- **Fix**: The backend [`src/sketchflow/main.py`](file:///home/ubuntu/Desktop/SketchFlow/src/sketchflow/main.py) uses `allow_origins=["*"]`, `allow_methods=["*"]`, `allow_headers=["*"]`. Ensure your backend service is running the latest code commit.
