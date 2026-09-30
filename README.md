# TraceGaurd

## Multi-Agent AI Incident Commander

TraceGaurd turns noisy incident signals into an evidence-backed investigation, explains the likely cause, retrieves relevant runbook knowledge, recommends safe next actions, and applies guardrails before production changes.

### Demo flow
1. Start the stack.
2. Open the dashboard.
3. Click **Simulate Incident**.
4. Select `INC-1001`.
5. TraceGaurd displays the incident evidence, root-cause hypothesis, confidence, investigation steps, agent trace, RAG context, and guarded actions.

### Architecture
`Simulated Logs / Alerts / Deployments / Tickets → FastAPI → Event Normalizer → Multi-Agent Engine → RAG → Root-Cause Analysis → Guardrails → Human Approval → Dashboard`

### Stack
- Frontend: React + Vite
- Backend: FastAPI + Python
- Agent orchestration: modular agent pipeline
- AI reasoning: evidence-based demo reasoning engine
- RAG: runbook retrieval layer
- Database: PostgreSQL-ready Docker service
- Deployment: Docker Compose
- Quality: Pytest + GitHub Actions

### Run with Docker

```bash
docker compose up --build
```

Dashboard: http://localhost:5173
API docs: http://localhost:8000/docs
Health: http://localhost:8000/health

### Run backend directly

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload
```

### Important demo note
The default demo does not require an external API key. It produces deterministic, evidence-backed investigation steps so the hackathon demo is reliable offline. An external LLM can be added behind the same analysis contract later.

### Safety model
- SAFE: read-only or reversible diagnostic actions
- APPROVAL: production mutations such as rollback
- BLOCKED: unknown or disallowed actions

TraceGaurd never executes a production mutation automatically in the prototype.
