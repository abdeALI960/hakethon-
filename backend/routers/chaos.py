from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.errors import AppError
from backend.models import Endpoint
from backend.schemas import (
    ChaosInjectionRequest,
    ChaosInjectionResponse,
    ErrorResponse,
)
from backend.services.executor import ChaosAction, DemoService, DemoTarget, execute_chaos
from backend.services.pipeline import create_injected_incident

router = APIRouter()

_PORT_BY_SERVICE = {
    DemoService.WEB: 5001,
    DemoService.API: 5002,
    DemoService.WORKER: 5003,
}
_CHAOS_ACTION_BY_TYPE = {
    "CRASH": ChaosAction.CRASH,
    "CPU_SPIKE": ChaosAction.CPU,
    "HIGH_LATENCY": ChaosAction.LATENCY,
    "OOM_KILL": ChaosAction.CRASH,
}
_ANOMALY_BY_TYPE = {
    "CRASH": "CRASH",
    "CPU_SPIKE": "CPU_SPIKE",
    "HIGH_LATENCY": "LATENCY",
    "OOM_KILL": "CRASH",
}
_SCRIPT_ACTION_BY_TYPE = {
    "CRASH": "crash",
    "CPU_SPIKE": "cpu",
    "HIGH_LATENCY": "latency",
    "OOM_KILL": "crash",
}


@router.post(
    "/chaos/inject",
    response_model=ChaosInjectionResponse,
    status_code=201,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def inject_chaos(
    payload: ChaosInjectionRequest,
    db: Session = Depends(get_db),
) -> ChaosInjectionResponse:
    try:
        service = DemoService(payload.service)
        target = DemoTarget(service, payload.port)
    except ValueError as exc:
        raise AppError("INVALID_DEMO_TARGET", "Service and port are not an allow-listed target.", 422) from exc
    endpoint = db.scalar(
        select(Endpoint).where(
            Endpoint.service_key == payload.service,
            Endpoint.port == payload.port,
            Endpoint.enabled.is_(True),
            Endpoint.is_demo_target.is_(True),
        )
    )
    if endpoint is None or _PORT_BY_SERVICE[service] != payload.port:
        raise AppError("DEMO_TARGET_NOT_REGISTERED", "Demo endpoint is not registered.", 403)
    result = await execute_chaos(_CHAOS_ACTION_BY_TYPE[payload.type.value], target)
    if not result.ok:
        raise AppError("CHAOS_INJECTION_FAILED", "Chaos injection could not be completed.", 502)
    create_injected_incident(db, endpoint, _ANOMALY_BY_TYPE[payload.type.value])
    command = (
        f"python inject.py {_SCRIPT_ACTION_BY_TYPE[payload.type.value]} "
        f"--target {payload.service}:{payload.port}"
    )
    return ChaosInjectionResponse(
        status="injected",
        command=command,
        target_pid=None,
    )
