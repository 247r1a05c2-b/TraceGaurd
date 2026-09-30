# TraceGaurd

## Multi-Agent AI Incident Commander

TraceGaurd converts noisy logs, alerts, deployments and tickets into an evidence-backed incident investigation. A LangGraph workflow coordinates specialized agents, a local vector RAG layer retrieves runbooks, and an LLM can produce the root-cause hypothesis and diagnosis plan. Guardrails classify every recommended action before it can reach a human reviewer.

### What the demo does
1. Start the FastAPI backend and React dashboard.
2. Click **Simulate Incident**.
3. Select the generated incident.
4. Watch the LangGraph agent trace execute.
5. Review the root-cause hypothesis and confidence.
6. Inspect the ordered diagnosis steps and their evidence.
7. Inspect the RAG runbooks retrieved for the incident.
8. Review the chronological evidence timeline.
9. Review guarded actions: SAFE, APPROVAL, or BLOCKED.

### Architecture

`Logs / Alerts / Deployments / Tickets → Ingestion → Noise Filter → Correlation → RAG Retrieval → Root Cause Agent → Diagnostic Agent → Guardrail Agent → Timeline Agent → React Dashboard`

### Multi-agent roles

| Agent | Responsibility |
|---|---|
| Ingestion Agent | Normalizes incident events into a shared state |
| Noise Filter Agent | Prioritizes critical and warning signals |
| Correlation Agent | Links deployments, symptoms, services and dependency failures |
| RAG Agent | Retrieves the most relevant runbooks with TF-IDF cosine similarity |
| Root Cause Agent | Uses LLM + incident evidence + retrieved runbooks to form a hypothesis |
| Diagnostic Agent | Produces ordered, evidence-backed investigation steps |
| Guardrail Agent | Applies default-deny safety classification to actions |
| Timeline Agent | Builds an auditable chronological incident history |

### Stack

- Frontend: React + Vite
- Backend: FastAPI + Python
- Agent orchestration: LangGraph StateGraph
- LLM: OpenAI through LangChain, optional via `OPENAI_API_KEY`
- RAG: local TF-IDF vector retrieval with cosine similarity
- Storage: in-memory demo store, PostgreSQL-ready structure
- Testing: Pytest
- Deployment: Docker files are included, but Docker is not required for local development

### Run without Docker

#### 1. Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000` and Swagger at `http://localhost:8000/docs`.

#### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL shown in the terminal, normally `http://localhost:5173`.

#### 3. Optional LLM mode

Copy `.env.example` to `.env` and set your OpenAI key:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Without a key, TraceGaurd still runs using the deterministic evidence-backed fallback. With a key, the Root Cause Agent and Diagnostic Agent use the LLM while the RAG and guardrail layers remain explicit and inspectable.

### Demo scenario

The built-in checkout scenario contains a deployment followed by HTTP 500 errors and database connection-pool timeout signals. TraceGaurd correlates those signals, retrieves the relevant runbooks, produces a root-cause hypothesis, and generates safe diagnosis steps before presenting any production mutation as requiring human approval.

### Safety model

- **SAFE**: read-only or reversible diagnostic actions
- **APPROVAL**: production mutations such as rollback or restart
- **BLOCKED**: destructive, unknown or disallowed actions

TraceGaurd does not execute production mutations automatically in the prototype.
