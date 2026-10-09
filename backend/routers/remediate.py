from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.errors import AppError
from backend.models import Endpoint, Incident, Remediation
from backend.schemas import ErrorResponse, RemediationRequest, RemediationResponse
from backend.services.executor import DemoService, FixAction
from backend.services.pipeline import remediate_incident

router = APIRouter()

_FIX_ACTION_BY_REQUEST_VALUE = {
    "restart": FixAction.RESTART,
    "python fixer.py restart api": FixAction.RESTART,
    "kill_spinloop": FixAction.KILL_SPINLOOP,
    'kill -SIGUSR1 $(pgrep -f "worker/spinloop")': FixAction.KILL_SPINLOOP,
    "clear_latency": FixAction.CLEAR_LATENCY,
    "curl -X POST http://127.0.0.1:5001/admin/reset-delay": FixAction.CLEAR_LATENCY,
}


@router.post(
    "/remediate",
    response_model=RemediationResponse,
    responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
async def remediate(
    payload: RemediationRequest,
    db: Session = Depends(get_db),
) -> RemediationResponse:
    incident = db.scalar(
        select(Incident)
        .where(
            Incident.service == payload.service,
            Incident.status == "awaiting_approval",
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
    )
    if incident is None:
        raise AppError("INCIDENT_NOT_AWAITING_APPROVAL", "No incident is awaiting approval.", 404)
    endpoint = db.scalar(
        select(Endpoint).where(
            Endpoint.service_key == payload.service,
            Endpoint.port == incident.port,
            Endpoint.enabled.is_(True),
            Endpoint.is_demo_target.is_(True),
        )
    )
    if endpoint is None:
        raise AppError(
            "DEMO_TARGET_NOT_REGISTERED",
            "Fixes may only target a registered demo endpoint.",
            403,
        )
    try:
        service = DemoService(payload.service)
    except ValueError as exc:
        raise AppError("INVALID_DEMO_TARGET", "Service is not an allow-listed target.", 422) from exc
    fix_action = _FIX_ACTION_BY_REQUEST_VALUE[payload.action.value]
    if (
        fix_action is FixAction.KILL_SPINLOOP and service is not DemoService.WORKER
    ) or (fix_action is FixAction.CLEAR_LATENCY and service is not DemoService.WEB):
        raise AppError(
            "INVALID_REMEDIATION_ACTION",
            "Remediation action is not supported for this service.",
            422,
        )
    incident = await remediate_incident(db, incident, endpoint, fix_action)
    remediation = db.scalar(
        select(Remediation)
        .where(Remediation.incident_id == incident.id)
        .order_by(Remediation.created_at.desc(), Remediation.id.desc())
        .limit(1)
    )
    return RemediationResponse(
        status="recovered" if incident.status == "verified" else "failed",
        new_pid=remediation.new_pid if remediation is not None else None,
        probe_verified=bool(remediation and remediation.probe_verified),
        fix_duration_sec=remediation.fix_duration_sec if remediation is not None else 0,
    )
