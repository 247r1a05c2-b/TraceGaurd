# TraceGaurd — Multi-Agent AI Incident Commander

TraceGaurd is a hackathon-ready incident operations platform for software engineers and SRE teams. A client sends operational signals; TraceGaurd normalizes them, runs a LangGraph multi-agent investigation, retrieves runbook knowledge with RAG, produces an evidence-backed root-cause hypothesis, evaluates confidence, applies a default-deny guardrail, requests human approval for production mutations, and only then runs a controlled remediation adapter.

## What changed in this version

- **Software engineer authentication** with an 8-hour signed session.
- **Client monitoring** with a service/environment inventory, incident counts and heartbeats.
- **Multi-agent incident flow:** Ingestion → Noise Filter → Correlation → RAG → Root Cause → Diagnostic → Guardrail → Timeline.
- **Evidence-backed confidence percentage** plus evaluation metrics for evidence coverage, workflow completeness and diagnosis quality.
- **Human-in-the-loop gate:** Guardrail classification happens before the engineer approval step; APPROVAL actions cannot execute without an explicit approval record.
- **Controlled automatic remediation:** after approval, TraceGaurd calls an allow-listed execution adapter. The demo adapter is simulated and never runs arbitrary shell/Kubernetes/database commands.
- **Audit trail** for logins, incident ingestion, client registration, human approvals and executions.
- **Responsive React dashboard** for client monitoring, incident queue, AI investigation, RAG evidence, agent trace, guardrail actions, metrics and timeline.
- **Deterministic fallback** works without an LLM API key; an OpenAI key enables the existing LLM root-cause and diagnostic generation.
- **Tests** cover authentication, protected APIs, analysis, metrics and approval-before-execution.

## Architecture

```text
Client Systems
  ├── Logs / Alerts / Deployments / Tickets
  └── Heartbeats
          ↓
Ingestion & Normalization
          ↓
LangGraph Multi-Agent Engine
  Ingestion → Noise Filter → Correlation → RAG
                    ↓
             Root Cause Agent
                    ↓
             Diagnostic Agent
                    ↓
             Guardrail Agent
                    ↓
          Human Engineer Approval
             ↙             ↘
          Reject        Approve
                           ↓
                 Controlled Executor
                           ↓
                    Audit Timeline
                           ↓
                    React Dashboard
```

## Agents

| Agent | Responsibility |
|---|---|
| Ingestion Agent | Normalizes heterogeneous events into a shared state |
| Noise Filter Agent | Prioritizes critical and warning signals |
| Correlation Agent | Connects deployments, failures, services and dependencies |
| RAG Agent | Retrieves relevant runbooks/knowledge |
| Root Cause Agent | Generates a defensible hypothesis from observed evidence |
| Diagnostic Agent | Creates ordered investigation steps and candidate actions |
| Guardrail Agent | Classifies actions as SAFE, APPROVAL or BLOCKED |
| Timeline Agent | Builds the auditable chronological evidence history |

## Confidence and evaluation

The dashboard shows a percentage for **root-cause confidence**. This is an evidence-supported hypothesis score, not a claim that the AI is certainly correct. The evaluation panel also exposes evidence coverage, workflow completeness and diagnosis quality so judges can see how the result was produced.

## Human approval and remediation

TraceGaurd intentionally separates **AI recommendation**, **guardrail classification**, **human approval**, and **execution**. An APPROVAL action cannot be executed by the API until the authenticated software engineer creates an approval record. The demo executor uses an explicit allow-list and returns `SIMULATED_SUCCESS`; connect a signed production-specific adapter before performing real infrastructure mutations.

## Run without Docker

### Backend — Windows

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
cd ..
uvicorn backend.app.main:app --reload --port 8000
```

### Frontend

Open another terminal:

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

For a real deployment, change these values with environment variables:

```text
DEMO_ENGINEER_EMAIL=your-engineer@example.com
DEMO_ENGINEER_PASSWORD=use-a-strong-secret
TRACEGAURD_SECRET=use-a-long-random-signing-secret
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

## Demo flow for the hackathon

1. Login as a software engineer.
2. See the monitored client/service inventory.
3. Click **Simulate Client Incident**.
4. Open the generated incident.
5. Show the LangGraph agent trace executing in order.
6. Show the RAG evidence and root-cause hypothesis.
7. Explain the confidence percentage and evaluation metrics.
8. Open Guardrail & Remediation.
9. Approve the production-style action as the human reviewer.
10. TraceGaurd executes the allow-listed demo adapter and records the action in the audit trail.

## Tests

```bash
python -m pytest -q
```

The test suite verifies that protected endpoints require login, incidents are analyzed through the agent pipeline, metrics are exposed, and an APPROVAL action cannot execute until an explicit human approval is recorded.

## Deployment

Docker files already exist for the project, but Docker is **not required** for the local hackathon demo. The frontend can be deployed to Vercel/Netlify and the FastAPI service to Render or another Python host.

## NexaRAG relationship

The separate `NexaRAG` repository contains reusable incident/RAG work. TraceGaurd is now the integrated application repository: its RAG layer, multi-agent workflow, client monitoring, human approval gate and dashboard are all exercised from one project. The RAG implementation can later be replaced by the richer NexaRAG knowledge service without changing the guardrail/approval contract.
