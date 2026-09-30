ARCHITECTURE = {
    "name": "TraceGaurd Multi-Agent Incident Commander",
    "layers": [
        {"id": "sources", "title": "Incident Data Sources", "components": [
            {"id": "logs", "label": "Logs", "description": "Application, system and error logs"},
            {"id": "alerts", "label": "Alerts", "description": "Monitoring and alerting signals"},
            {"id": "deployments", "label": "Deployments", "description": "CI/CD, Git and version changes"},
            {"id": "tickets", "label": "Tickets / Chat", "description": "Support, chat and service desk context"},
        ]},
        {"id": "ingestion", "title": "Ingestion & Normalization Layer", "description": "Collect, validate, authenticate and normalize telemetry into the common incident event model."},
        {"id": "agents", "title": "Multi-Agent AI Engine", "technology": ["LangGraph", "LLM", "RAG"], "components": [
            {"id": "ingestion-agent", "label": "Ingestion Agent", "purpose": "Normalize incoming events"},
            {"id": "noise-filter-agent", "label": "Noise Filter Agent", "purpose": "Prioritize useful signals"},
            {"id": "correlation-agent", "label": "Correlation Agent", "purpose": "Link changes, time and services"},
            {"id": "rag-agent", "label": "RAG Agent", "purpose": "Retrieve runbooks and historical evidence"},
            {"id": "root-cause-agent", "label": "Root Cause Agent", "purpose": "Generate an evidence-backed hypothesis"},
            {"id": "diagnostic-agent", "label": "Diagnostic Agent", "purpose": "Generate reversible investigation steps"},
            {"id": "guardrail-agent", "label": "Guardrail Agent", "purpose": "Classify SAFE / APPROVAL / BLOCKED"},
            {"id": "timeline-agent", "label": "Timeline Agent", "purpose": "Maintain auditable incident history"},
        ]},
        {"id": "rag", "title": "RAG Layer", "components": [
            {"id": "runbooks", "label": "Runbooks", "description": "SOPs and incident playbooks"},
            {"id": "historical", "label": "Historical Incidents", "description": "Reusable incident knowledge"},
            {"id": "retriever", "label": "Vector Retrieval", "description": "Local TF-IDF vector retrieval with a replaceable pgvector/Chroma adapter"},
        ]},
        {"id": "data", "title": "PostgreSQL / Event Persistence", "components": [
            {"id": "postgres", "label": "PostgreSQL", "description": "Users, clients, approvals, audit and metadata"},
            {"id": "events", "label": "Incident Events", "description": "Normalized telemetry evidence"},
        ]},
        {"id": "llm", "title": "LLM Layer", "components": [
            {"id": "openai", "label": "OpenAI", "description": "Structured RCA and diagnostic reasoning when configured"},
            {"id": "fallback", "label": "Safety Fallback", "description": "Deterministic reasoning keeps the workflow runnable without a key"},
        ]},
        {"id": "human", "title": "Human-in-the-Loop", "description": "Software engineers review evidence, confidence and proposed actions before production mutation."},
        {"id": "dashboard", "title": "React / TypeScript Web Dashboard", "components": ["Incident Overview", "AI Analysis", "Safe Diagnostics", "RAG Evidence", "Agent Trace", "Approvals", "Audit Timeline", "Evaluation Metrics"]},
        {"id": "deployment", "title": "Deployment & Infrastructure", "components": ["Vercel / Render", "PostgreSQL", "Docker", "GitHub Actions"]},
    ],
    "flow": ["logs|ingestion", "alerts|ingestion", "deployments|ingestion", "tickets|ingestion", "ingestion|agents", "agents|rag", "rag|agents", "agents|data", "agents|llm", "llm|human", "human|agents", "agents|dashboard", "data|dashboard", "dashboard|human"]
}
