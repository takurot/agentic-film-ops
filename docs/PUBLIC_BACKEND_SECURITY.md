# Agentic FilmOps — Public Backend Security & Cloud Run Runbook

This document details the threat model, trust boundaries, configuration controls, and deployment runbooks for running the Agentic FilmOps backend in a secure, internet-exposed environment (e.g. Google Cloud Run) per Issue #88 and SPEC §3.4.

---

## 1. Threat Model & Trust Boundaries

```text
  [ Public Internet / Untrusted Clients ]
                     │
                     ▼
  [ Google Cloud Armor / Cloud Run Reverse Proxy ]
   - DDoS mitigation & HTTPS termination
   - Injects X-Forwarded-For client IP
                     │
                     ▼
  [ Agentic FilmOps ASGI Security Middleware Layer ]
   ├─ RequestBodySizeLimitASGIMiddleware (64 KB max)
   ├─ SecurityHeadersASGIMiddleware (nosniff, DENY, strict CSP)
   └─ CORSMiddleware (Strict allowed origin whitelist)
                     │
                     ▼
  [ FastAPI Route Dependencies & Application Security ]
   ├─ verify_demo_auth (Constant-time token validation if FILMOPS_REQUIRE_AUTH=true)
   ├─ enforce_mutation_rate_limit (Sliding-window IP rate limiting)
   ├─ enforce_reset_rate_limit (Demo reset rate limiting)
   └─ Concurrency Limiter (Max concurrent active Gemini analyses)
                     │
                     ▼
  [ Production Orchestrator & MCP stdio Subprocesses ]
   ├─ In-process isolated SQLite database / state machine
   ├─ Standalone stdio MCP servers (JSON-RPC 2.0)
   └─ Gemini 2.5 Flash via Google Gen AI SDK (Server-side API key)
```

### Trust Boundary Rules
1. **Never Trust the Client:** The UI never directly calls agents or mutates backend models. All state changes flow strictly through `/api/incidents/{id}/analyze`, `/api/analyses/{id}/decision`, or `/api/demo/reset`.
2. **Secret Boundary:** `GEMINI_API_KEY` and session tokens are loaded exclusively into server memory via environment variables / GCP Secret Manager. Secrets are never transmitted in API responses, logs, or client-side bundles.
3. **Fail-Closed Principle:** If live Gemini credentials or MCP servers are unavailable, the backend fails with explicit `503 Service Unavailable` or `500 Internal Server Error` with redacted details. It never silently masquerades failure as success.

---

## 2. Environment Variables & Security Configuration

| Variable | Default | Purpose | Production / Cloud Run Recommendation |
|---|---|---|---|
| `FILMOPS_ALLOWED_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000,https://takurot0708.web.app,https://takurot0708.firebaseapp.com` | Whitelist of allowed CORS origins | Set to exact Firebase Hosting domains: `https://takurot0708.web.app,https://takurot0708.firebaseapp.com` |
| `FILMOPS_REQUIRE_AUTH` | `false` | When `true`, requires valid session token on mutating endpoints | Set to `true` for private or judge-restricted deployments |
| `FILMOPS_AUTH_TOKEN` | *None* | Shared secret / bearer token verified with constant-time comparison | Inject from GCP Secret Manager |
| `FILMOPS_MAX_REQUEST_BODY_BYTES` | `65536` (64 KB) | Maximum incoming request body size to prevent memory DoS | `65536` |
| `FILMOPS_RATE_LIMIT_MUTATE` | `30` | Max mutation requests per minute per client IP | `15` to `30` |
| `FILMOPS_RATE_LIMIT_RESET` | `10` | Max demo reset requests per minute per client IP | `5` |
| `FILMOPS_MAX_CONCURRENT_ANALYSES` | `2` | Max concurrent active Gemini analysis jobs to prevent quota depletion | `2` to `4` |
| `GEMINI_API_KEY` | *None* | Google Gemini API key | Inject securely from GCP Secret Manager (`projects/$PROJECT_ID/secrets/gemini-api-key`) |

---

## 3. Google Cloud Run Deployment Runbook

### Step 1: Store Secrets in GCP Secret Manager
```bash
# Create secret for Gemini API key
gcloud secrets create gemini-api-key --data-file=- <<< "$GEMINI_API_KEY"

# (Optional) Create secret for demo session auth token
gcloud secrets create filmops-auth-token --data-file=- <<< "$(openssl rand -hex 32)"
```

### Step 2: Build & Deploy Container to Cloud Run
```bash
# Build backend container
gcloud builds submit --tag gcr.io/$PROJECT_ID/agentic-film-ops-backend:latest backend/

# Deploy to Cloud Run with security configuration
gcloud run deploy agentic-film-ops-backend \
  --image gcr.io/$PROJECT_ID/agentic-film-ops-backend:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars FILMOPS_RUNTIME_MODE=LIVE_GEMINI,FILMOPS_ALLOWED_ORIGINS="https://takurot0708.web.app,https://takurot0708.firebaseapp.com",FILMOPS_MAX_CONCURRENT_ANALYSES=2 \
  --set-secrets GEMINI_API_KEY=gemini-api-key:latest \
  --concurrency 80 \
  --cpu 1 \
  --memory 512Mi
```

---

## 4. Quota Monitoring, Cost Alerts & Kill-Switch

### 1. Cost & Quota Monitoring
- Configure Google Cloud Billing Budget alerts at $25, $50, and $100 thresholds.
- Monitor Gemini API tokens per minute (TPM) and requests per minute (RPM) in Google AI Studio dashboard.

### 2. Emergency Kill-Switch Procedures
If unexpected traffic or malicious abuse is detected:

1. **Disable Cloud Run Service Instantly:**
   ```bash
   gcloud run services update agentic-film-ops-backend --max-instances 0
   ```
2. **Revoke / Rotate Gemini API Key:**
   ```bash
   # Create a new key in Google AI Studio and update Secret Manager:
   gcloud secrets versions add gemini-api-key --data-file=- <<< "$NEW_GEMINI_API_KEY"
   ```
3. **Frontend Immediate Fallback:**
   The public Firebase frontend is deployed in `RECORDED_REPLAY` mode by default, meaning users and judges can continue evaluating the complete UI, scenario, and metrics 100% offline without backend dependency.
