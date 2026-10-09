from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class Base(DeclarativeBase):
    pass


class Endpoint(Base):
    __tablename__ = "endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    service_key = mapped_column(String(32), nullable=True)
    port = mapped_column(Integer, nullable=True)
    probe_interval_seconds: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_demo_target: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class ProbeResult(Base):
    __tablename__ = "probe_results"
    __table_args__ = (
        Index("ix_probe_results_endpoint_checked", "endpoint_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    endpoint_id: Mapped[int] = mapped_column(ForeignKey("endpoints.id"), nullable=False)
    http_status = mapped_column(Integer, nullable=True)
    ping_latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    ssl_cert_days = mapped_column(Integer, nullable=True)
    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_created_at", "created_at"),
        Index("ix_incidents_service", "service"),
    )

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    service: Mapped[str] = mapped_column(String(80), nullable=False)
    port = mapped_column(Integer, nullable=True)
    anomaly_type: Mapped[str] = mapped_column(String(20), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    auto_healed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    injected_at = mapped_column(DateTime(timezone=True), nullable=True)
    detected_at = mapped_column(DateTime(timezone=True), nullable=True)
    diagnosed_at = mapped_column(DateTime(timezone=True), nullable=True)
    fixed_at = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class IncidentLog(Base):
    __tablename__ = "incident_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    level: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(String(2000), nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Analysis(Base):
    __tablename__ = "analyses"
    __table_args__ = (
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    llm_status: Mapped[str] = mapped_column(String(16), nullable=False)
    root_cause: Mapped[str] = mapped_column(String(2000), nullable=False)
    confidence = mapped_column(Float, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(String(2000), nullable=False)
    raw_report: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class Remediation(Base):
    __tablename__ = "remediations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    executed_by: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    new_pid = mapped_column(Integer, nullable=True)
    probe_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    fix_duration_sec: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class RuntimeSettings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    llm_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="openai")
    p99_latency_sla_ms: Mapped[float] = mapped_column(Float, nullable=False, default=1000.0)
    webhook_url = mapped_column(String(1000), nullable=True)
    zero_touch_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    operator_name: Mapped[str] = mapped_column(String(120), nullable=False, default="OpsPilot")


class EmergencyCase(Base):
    __tablename__ = "emergency_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[str] = mapped_column(String(16), nullable=False, unique=True)
    incident_type: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str] = mapped_column(String(300), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    reported_by: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="Dispatched")
    ai_triage_summary: Mapped[str] = mapped_column(String(2000), nullable=False)
    llm_status: Mapped[str] = mapped_column(String(16), nullable=False, default="failed")
    evidence_path = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )
