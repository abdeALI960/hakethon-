from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.errors import AppError
from backend.models import Analysis, Incident, IncidentLog, utc_iso
from backend.schemas import (
    ErrorResponse,
    IncidentListResponse,
    IncidentLogResponse,
    IncidentResponse,
)
from backend.services.redaction import redact_text

router = APIRouter()


def _duration_seconds(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    return round((end - start).total_seconds(), 3)


def _incident_response(db: Session, incident: Incident) -> IncidentResponse:
    analysis = db.scalar(
        select(Analysis)
        .where(Analysis.incident_id == incident.id)
        .order_by(Analysis.created_at.desc(), Analysis.id.desc())
        .limit(1)
    )
    logs = db.scalars(
        select(IncidentLog)
        .where(IncidentLog.incident_id == incident.id)
        .order_by(IncidentLog.ts, IncidentLog.id)
    ).all()
    return IncidentResponse(
        id=incident.id,
        service=redact_text(incident.service),
        port=incident.port,
        anomaly_type=incident.anomaly_type,
        severity="CRITICAL" if incident.severity == "CRIT" else "MEDIUM",
        auto_healed=incident.auto_healed,
        status=incident.status,
        injected_at=utc_iso(incident.injected_at) if incident.injected_at else None,
        detected_at=utc_iso(incident.detected_at) if incident.detected_at else None,
        diagnosed_at=utc_iso(incident.diagnosed_at) if incident.diagnosed_at else None,
        fixed_at=utc_iso(incident.fixed_at) if incident.fixed_at else None,
        verified_at=utc_iso(incident.verified_at) if incident.verified_at else None,
        detection_duration_sec=_duration_seconds(incident.injected_at, incident.detected_at),
        fix_duration_sec=_duration_seconds(incident.detected_at, incident.verified_at),
        ai_rationale=redact_text(analysis.rationale) if analysis else None,
        logs=[
            IncidentLogResponse(
                ts=utc_iso(log.ts),
                level=log.level,
                message=redact_text(log.message),
            )
            for log in logs
        ],
    )


def _markdown_text(value: object) -> str:
    return (
        redact_text(value)
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("|", "\\|")
    )


def _seconds_text(value: float | None) -> str:
    return f"{value:.3f}s" if value is not None else "N/A"


@router.get("/incidents", response_model=IncidentListResponse)
def list_incidents(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: str | None = Query(default=None, max_length=80),
    status: str | None = Query(default=None, max_length=32),
    db: Session = Depends(get_db),
) -> IncidentListResponse:
    statement = select(Incident)
    count_statement = select(func.count(Incident.id))
    if service:
        statement = statement.where(Incident.service == service)
        count_statement = count_statement.where(Incident.service == service)
    if status:
        statement = statement.where(Incident.status == status)
        count_statement = count_statement.where(Incident.status == status)
    incidents = db.scalars(
        statement.order_by(Incident.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return IncidentListResponse(
        incidents=[_incident_response(db, incident) for incident in incidents],
        total=db.scalar(count_statement) or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/incidents/export.md",
    response_model=str,
    response_class=PlainTextResponse,
)
def export_incidents_markdown(db: Session = Depends(get_db)) -> str:
    incidents = db.scalars(select(Incident).order_by(Incident.created_at.desc())).all()
    mttd_values = [
        seconds
        for incident in incidents
        if (
            seconds := _duration_seconds(incident.injected_at, incident.detected_at)
        )
        is not None
    ]
    mttr_values = [
        seconds
        for incident in incidents
        if (
            seconds := _duration_seconds(incident.detected_at, incident.verified_at)
        )
        is not None
    ]
    healed_count = sum(incident.auto_healed for incident in incidents)
    healed_rate = healed_count / len(incidents) * 100 if incidents else 0.0
    average_mttd = sum(mttd_values) / len(mttd_values) if mttd_values else None
    average_mttr = sum(mttr_values) / len(mttr_values) if mttr_values else None

    lines = [
        "# OpsPilot Day 5 Demo Report",
        f"Date: {utc_iso(datetime.now(timezone.utc))}",
        f"Total Incidents: {len(incidents)}",
        f"Autonomous Healing Rate: {healed_rate:.1f}%",
        f"Average MTTD: {_seconds_text(average_mttd)}",
        f"Average MTTR: {_seconds_text(average_mttr)}",
        "",
        "## Executive Summary",
        (
            "OpsPilot monitored configured cluster endpoints. "
            f"{len(incidents)} incidents are included in this post-mortem export; "
            f"{healed_count} were recorded as autonomously healed."
        ),
        "",
        "## Incidents Post-Mortem Log",
    ]
    for index, incident in enumerate(incidents):
        if index:
            lines.extend(["", "---", ""])
        analysis = db.scalar(
            select(Analysis)
            .where(Analysis.incident_id == incident.id)
            .order_by(Analysis.created_at.desc(), Analysis.id.desc())
            .limit(1)
        )
        logs = db.scalars(
            select(IncidentLog)
            .where(IncidentLog.incident_id == incident.id)
            .order_by(IncidentLog.ts, IncidentLog.id)
        ).all()
        timestamp = incident.injected_at or incident.created_at
        target = (
            f"{incident.service}:{incident.port}"
            if incident.port is not None
            else incident.service
        )
        ai_diagnostic = (
            f"{analysis.recommended_action}: {analysis.rationale}"
            if analysis
            else "No AI diagnosis recorded"
        )
        lines.extend(
            [
                f"### {_markdown_text(incident.id)}: "
                f"{_markdown_text(incident.anomaly_type)} on {_markdown_text(target)}",
                f"- **Timestamp**: {utc_iso(timestamp)}",
                f"- **Status**: {_markdown_text(incident.status)}",
                "- **Detection (MTTD)**: "
                f"{_seconds_text(_duration_seconds(incident.injected_at, incident.detected_at))}",
                "- **Remediation (MTTR)**: "
                f"{_seconds_text(_duration_seconds(incident.detected_at, incident.verified_at))}",
                f"- **Evidence Snapshot**: {_markdown_text(target)} — "
                f"{_markdown_text(incident.anomaly_type)}",
                f"- **AI Diagnostic**: {_markdown_text(ai_diagnostic)}",
                "- **Telemetry Logs**:",
            ]
        )
        if logs:
            lines.extend(
                f"  - [{utc_iso(log.ts)}] [{_markdown_text(log.level)}] "
                f"{_markdown_text(log.message)}"
                for log in logs
            )
        else:
            lines.append("  - No telemetry logs recorded")
    lines.extend(
        [
            "",
            "Generated by OpsPilot Telemetry Core Daemon v1.2.4",
            "",
        ]
    )
    return "\n".join(lines)


@router.get(
    "/incidents/{incident_id}",
    response_model=IncidentResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
) -> IncidentResponse:
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise AppError("INCIDENT_NOT_FOUND", "Incident was not found.", 404)
    return _incident_response(db, incident)
