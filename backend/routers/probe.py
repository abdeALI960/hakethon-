import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Endpoint, Incident, ProbeResult, RuntimeSettings, utc_iso
from backend.schemas import ErrorResponse, ProbeResponse, ServiceHealth
from backend.services.probe import probe_endpoint
from backend.services.url_security import validate_target_url

router = APIRouter()


@router.get(
    "/probe",
    response_model=ProbeResponse,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def probe_target(
    url: str = Query(min_length=1, max_length=2000),
    db: Session = Depends(get_db),
) -> ProbeResponse:
    await validate_target_url(db, url)
    async with httpx.AsyncClient(timeout=3, follow_redirects=False) as client:
        result = await probe_endpoint(client, url, timeout_seconds=3)
    return ProbeResponse(
        http_status=result.http_status,
        ping_latency_ms=result.ping_latency_ms,
        ssl_cert_days=result.ssl_cert_days,
        last_checked_utc=utc_iso(result.checked_at),
    )


@router.get("/services/health", response_model=list[ServiceHealth])
def services_health(db: Session = Depends(get_db)) -> list[ServiceHealth]:
    endpoints = db.scalars(select(Endpoint).where(Endpoint.enabled.is_(True))).all()
    runtime = db.get(RuntimeSettings, 1)
    sla_ms = runtime.p99_latency_sla_ms if runtime is not None else 1000
    results: list[ServiceHealth] = []
    for endpoint in endpoints:
        latest = db.scalar(
            select(ProbeResult)
            .where(ProbeResult.endpoint_id == endpoint.id)
            .order_by(ProbeResult.checked_at.desc(), ProbeResult.id.desc())
            .limit(1)
        )
        active_incident = db.scalar(
            select(Incident)
            .where(
                Incident.service == (endpoint.service_key or endpoint.name),
                Incident.status.in_(
                    ("injected", "detected", "diagnosed", "fixed", "awaiting_approval")
                ),
            )
            .order_by(Incident.created_at.desc())
            .limit(1)
        )
        if active_incident and active_incident.status == "fixed":
            status = "recovering"
        elif latest is None:
            status = "degraded"
        elif not latest.ok:
            status = "critical"
        elif latest.ping_latency_ms > sla_ms or active_incident is not None:
            status = "degraded"
        else:
            status = "healthy"
       latency_ms=latest.ping_latency_ms if latest else 0,
    return results
