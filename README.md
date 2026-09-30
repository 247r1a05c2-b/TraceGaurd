# TraceGaurd

Multi-Agent AI Incident Commander for Safe Autonomous Incident Analysis.

## Phase 1
- FastAPI backend
- Simulated incident ingestion
- Event normalization
- Incident/event APIs
- PostgreSQL-ready data model
- Automated tests

## Run locally

\`\`\`bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
\`\`\`

Open http://127.0.0.1:8000/docs
