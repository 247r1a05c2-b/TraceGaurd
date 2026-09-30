# TraceGaurd deployment and demo guide

TraceGaurd is split into a React/Vite frontend and FastAPI backend. The backend exposes the complete incident workflow: client ingestion → LangGraph agents → RAG → root-cause hypothesis → diagnosis → guardrail classification → human approval → controlled remediation → audit/metrics.

## 1. Local run without Docker

Use Python 3.12 for the backend.

```text
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```text
cd frontend
npm install
npm run dev
```

Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local` if needed.

## 2. Required environment variables

Copy `.env.example` to the backend environment and set:

- `TRACEGAURD_SECRET`: long random secret used for engineer sessions.
- `TRACEGAURD_CLIENT_INGEST_SECRET`: different long random secret used to authenticate monitored client event senders.
- `DEMO_ENGINEER_EMAIL` and `DEMO_ENGINEER_PASSWORD`: engineer login credentials.
- `DATABASE_URL`: PostgreSQL URL for persistent deployment; SQLite is the local fallback.
- `OPENAI_API_KEY`: optional. Without it, deterministic fallback agents still complete the workflow.
- `OPENAI_MODEL`: model used by the Root Cause and Diagnostic agents when an API key is configured.

## 3. Client monitoring API

Register a client from the engineer dashboard/API. The returned `client_id` identifies the monitored service.

Client systems can send normalized events to:

```text
POST /api/v1/client/events
X-TraceGaurd-Client-ID: <client_id>
X-TraceGaurd-Signature: HMAC_SHA256(TRACEGAURD_CLIENT_INGEST_SECRET, client_id)
Content-Type: application/json
```

The request body is the same `IngestRequest` schema accepted by `/api/v1/events`.

This endpoint is intentionally separate from engineer authentication: client telemetry uses a signed service identity, while the dashboard and remediation controls require a software-engineer session.

## 4. Incident lifecycle

```text
Client event
   ↓
Ingestion Agent
   ↓
Noise Filter Agent
   ↓
Correlation Agent
   ↓
RAG Agent
   ↓
Root Cause Agent (LLM when configured, deterministic fallback otherwise)
   ↓
Diagnostic Agent
   ↓
Guardrail Agent
   ↓
Human engineer approval
   ↓
Allow-listed remediation adapter
   ↓
Verification + Audit Timeline
```

The remediation adapter is deliberately simulated. TraceGaurd never turns an LLM-generated command directly into a shell, Kubernetes, database, or cloud mutation.

## 5. Vercel deployment

Create two Vercel projects from the same GitHub repository:

### Backend project

- Root Directory: `backend`
- Framework: Other / FastAPI entrypoint
- The repository already contains `backend/api/index.py` and `backend/vercel.json`.
- Configure `DATABASE_URL`, `TRACEGAURD_SECRET`, `TRACEGAURD_CLIENT_INGEST_SECRET`, `DEMO_ENGINEER_EMAIL`, `DEMO_ENGINEER_PASSWORD`, `OPENAI_API_KEY`, and `OPENAI_MODEL`.

### Frontend project

- Root Directory: `frontend`
- Framework: Vite
- Configure `VITE_API_URL` to the deployed backend URL.

For a hosted deployment, use PostgreSQL rather than SQLite so incidents, approvals and audit records survive serverless restarts.

## 6. Tests

```text
pip install -r backend/requirements.txt
pytest backend/tests -q
```

The suite covers authentication, protected APIs, the full eight-agent graph, evaluation metrics, human approval before execution, and signed client ingestion.

## 7. Hackathon demo

1. Open the frontend and sign in as the software engineer.
2. Show the monitored client inventory.
3. Trigger `Simulate Client Incident` or send a signed client event.
4. Open the incident and show the eight-stage LangGraph trace.
5. Show RAG evidence and the evidence-supported root-cause confidence percentage.
6. Show ordered diagnosis/repair steps.
7. Open Guardrail & Human Approval.
8. Approve the allow-listed production-style action.
9. Show the controlled simulated remediation and verification results.
10. Show evaluation metrics and audit timeline.
