# TraceGaurd — Multi-Agent AI Incident Commander

TraceGaurd is a ready-to-demo incident operations platform for software engineers and SRE teams. A monitored client sends operational signals; TraceGaurd normalizes them, runs a **LangGraph multi-agent investigation**, retrieves relevant runbooks and historical incidents with **RAG**, uses **Gemini LLM** reasoning when `GEMINI_API_KEY` is available, produces an evidence-backed root-cause hypothesis and diagnosis steps, evaluates confidence and workflow metrics, applies a default-deny safety gate, requests explicit human approval for production mutations, and only then runs a controlled remediation adapter.

## Complete flow

```text
Software Engineer Login
        ↓
Client Monitoring / Heartbeats / Health Checks
        ↓
Incident Ingestion
        ↓
LangGraph Multi-Agent Workflow
        │
        ├── Ingestion Agent
        ├── Noise Filter Agent
        ├── Correlation Agent
        ├── RAG Agent ──→ Runbooks + Historical Incidents
        ├── Root Cause Agent ──→ Gemini LLM + evidence
        ├── Diagnostic Agent ──→ Gemini LLM + safe steps
        ├── Guardrail Agent ──→ SAFE / APPROVAL / BLOCKED
        └── Timeline Agent
                ↓
       Root Cause + Confidence %
                ↓
       Diagnosis Steps + Actions
                ↓
          Human Engineer Gate
             ↙           ↘
          Reject        Approve
                          ↓
                 Controlled Executor
                          ↓
                    Verification
                          ↓
                     Audit Trail
```

## Requirements covered

- **Software engineer login:** protected API with an 8-hour signed session.
- **Client monitoring:** register clients, track environment/service, heartbeat, website health checks, incidents and performance score.
- **Multi-agent diagnosis:** LangGraph executes the complete ordered agent workflow.
- **RAG:** retrieves relevant internal runbooks and historical incidents; Gemini Google Search grounding can add current external technical evidence when configured.
- **LLM:** Gemini generates structured root-cause hypotheses and diagnostic plans from incident evidence and retrieved knowledge. The system falls back to deterministic analysis if Gemini is unavailable.
- **Root cause:** evidence-backed hypothesis with confidence percentage.
- **Diagnosis steps:** ordered, auditable steps showing what to verify and why.
- **Guardrail:** every proposed action is classified before execution.
- **Human acceptance:** APPROVAL actions cannot execute without an explicit authenticated engineer approval record.
- **Auto-solve path:** after approval, the controlled executor can run an allow-listed remediation adapter. The included demo adapter is simulated and never executes arbitrary shell, Kubernetes or database commands.
- **Evaluation metrics:** evidence coverage, workflow completeness, diagnosis quality and per-agent trace metrics are exposed to the dashboard.
- **Auditability:** login, client registration, incident ingestion, approvals and executions are persisted in the audit trail.

## RAG + LLM explanation

TraceGaurd deliberately separates retrieval from generation:

1. The **RAG Agent** searches the local knowledge base using TF-IDF semantic-style retrieval and returns relevant runbook/historical evidence.
2. When `GEMINI_API_KEY` is configured, the retrieval layer also uses Gemini Google Search grounding for authoritative external technical sources.
3. The **Root Cause Agent** receives observed incident events plus retrieved knowledge and asks Gemini to return a structured JSON hypothesis.
4. The **Diagnostic Agent** receives the same evidence and generates ordered diagnosis steps and candidate actions.
5. Guardrails operate after generation so the LLM cannot bypass the human approval boundary.

This means the project demonstrates both technologies clearly: **RAG supplies evidence; the LLM reasons over that evidence.**

## Run locally without Docker

### Backend

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`.

### Demo login

```text
Email: engineer@tracegaurd.ai
Password: TraceGaurd@123
```

The demo credentials work without additional configuration. For deployment, set these environment variables:

```text
GEMINI_API_KEY=<your existing Gemini key>
GEMINI_MODEL=gemini-2.5-flash
TRACEGAURD_SECRET=<long random secret>
DEMO_ENGINEER_EMAIL=your-engineer@example.com
DEMO_ENGINEER_PASSWORD=<strong password>
DATABASE_URL=<optional PostgreSQL URL>
```

`DATABASE_URL` is optional for a local/demo run because TraceGaurd automatically uses SQLite. For persistent cloud deployment, use PostgreSQL.

## Hackathon demo

1. Log in as the software engineer.
2. Register or select a monitored client.
3. Run **Simulate Client Incident** or ingest real-looking logs/alerts/deployments.
4. Open the incident.
5. Run **Multi-Agent Analysis**.
6. Show the LangGraph agent trace.
7. Show RAG evidence retrieved from runbooks/history and external technical sources when Gemini grounding is available.
8. Show Gemini-generated root cause, confidence percentage and evidence.
9. Show the ordered diagnosis steps.
10. Open Guardrail & Remediation.
11. Approve an APPROVAL action as the human reviewer.
12. Execute the controlled demo remediation.
13. Show verification and the audit timeline.

## API

Key endpoints include:

- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `GET /api/v1/clients`
- `POST /api/v1/clients`
- `POST /api/v1/clients/{client_id}/heartbeat`
- `POST /api/v1/clients/{client_id}/check`
- `POST /api/v1/clients/{client_id}/simulate-incident`
- `GET /api/v1/incidents`
- `GET /api/v1/incidents/{incident_id}/events`
- `GET /api/v1/incidents/{incident_id}/analysis`
- incident approval/execution endpoints
- database status and evaluation endpoints

## Safety

TraceGaurd does not give the LLM unrestricted infrastructure access. The system separates recommendation, guardrail classification, human approval, execution and verification. The bundled executor is intentionally simulated/allow-listed for the hackathon.

## Deployment

The repository contains Vercel configuration for the Vite frontend and FastAPI backend. Configure the existing Gemini key in the Vercel project's server-side environment variables. Set `TRACEGAURD_SECRET` and a strong demo-engineer password for a real deployment. Use PostgreSQL if the deployment must persist data across serverless instances.
