from datetime import datetime, timezone
from statistics import fmean, pstdev

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Incident, Remediation
from backend.schemas import DurationStats, KpiResponse, MttrStats

router = APIRouter()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


@router.get("/kpis", response_model=KpiResponse)
def get_kpis(db: Session = Depends(get_db)) -> KpiResponse:
    incidents = db.scalars(select(Incident)).all()
    mttd_samples = [
        (_as_utc(incident.detected_at) - _as_utc(incident.injected_at)).total_seconds()
        for incident in incidents
        if incident.injected_at is not None and incident.detected_at is not None
    ]
    mttr_samples = [
        (_as_utc(incident.verified_at) - _as_utc(incident.detected_at)).total_seconds()
        for incident in incidents
        if incident.detected_at is not None and incident.verified_at is not None
    ]
    total = len(incidents)
    auto_healed = sum(incident.auto_healed for incident in incidents)
    human_incident_ids = set(
        db.scalars(
            select(Remediation.incident_id).where(Remediation.executed_by == "human")
        ).all()
    )
    human_escalations = sum(
        incident.status == "awaiting_approval"
        or incident.id in human_incident_ids
        for incident in incidents
    )
    return KpiResponse(
        total_incidents=total,
        auto_healed_rate_percent=round(auto_healed * 100 / total, 2) if total else 0.0,
        human_escalations=human_escalations,
        mttd_seconds=DurationStats(
            avg=round(fmean(mttd_samples), 3) if mttd_samples else 0.0,
            std_dev=round(pstdev(mttd_samples), 3) if mttd_samples else 0.0,
        ),
        mttr_seconds=MttrStats(
            avg=round(fmean(mttr_samples), 3) if mttr_samples else 0.0,
        ),
    )
