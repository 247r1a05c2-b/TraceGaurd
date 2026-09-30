from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "tracegaurd.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ClientRecord(Base):
    __tablename__ = "clients"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    environment: Mapped[str] = mapped_column(String(50))
    service: Mapped[str] = mapped_column(String(120))
    incidents: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(30), default="ONLINE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class IncidentRecord(Base):
    __tablename__ = "incidents"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    client_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    title: Mapped[str] = mapped_column(String(250))
    severity: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), default="OPEN")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class IncidentEventRecord(Base):
    __tablename__ = "incident_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    timestamp: Mapped[str] = mapped_column(String(64))
    source: Mapped[str] = mapped_column(String(80))
    service: Mapped[str] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(30))
    message: Mapped[str] = mapped_column(Text)


class AgentRunRecord(Base):
    __tablename__ = "agent_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    agent: Mapped[str] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30))
    output: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class DiagnosisStepRecord(Base):
    __tablename__ = "diagnosis_steps"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    stage: Mapped[str] = mapped_column(String(150))
    finding: Mapped[str] = mapped_column(Text)
    evidence: Mapped[str] = mapped_column(Text)


class RepairActionRecord(Base):
    __tablename__ = "repair_actions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(250))
    risk: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="PROPOSED")
    reason: Mapped[str] = mapped_column(Text)


class ApprovalRecord(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(250))
    engineer: Mapped[str] = mapped_column(String(250))
    state: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class RemediationExecutionRecord(Base):
    __tablename__ = "remediation_executions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    incident_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(250))
    engineer: Mapped[str] = mapped_column(String(250))
    status: Mapped[str] = mapped_column(String(40))
    verification: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class AuditRecord(Base):
    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event: Mapped[str] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(250))
    details: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


init_db()
