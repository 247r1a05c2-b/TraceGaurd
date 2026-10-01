from sqlalchemy import text

from .database import engine, IS_SQLITE


INDEX_STATEMENTS = (
    "CREATE INDEX IF NOT EXISTS idx_clients_status ON clients (status)",
    "CREATE INDEX IF NOT EXISTS idx_clients_created_at ON clients (created_at)",
    "CREATE INDEX IF NOT EXISTS idx_incidents_client_created ON incidents (client_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_incidents_status_created ON incidents (status, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_incident_events_incident_timestamp ON incident_events (incident_id, timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_audit_created_at ON audit_events (created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_approvals_incident_created ON approvals (incident_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_remediation_incident_created ON remediation_executions (incident_id, created_at DESC)",
)


def ensure_indexes() -> None:
    with engine.begin() as connection:
        for statement in INDEX_STATEMENTS:
            connection.execute(text(statement))
        if not IS_SQLITE:
            connection.execute(text("ANALYZE"))
