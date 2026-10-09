from urllib.parse import urlsplit

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.errors import AppError
from backend.models import Endpoint, ProbeResult, utc_iso
from backend.schemas import (
    EndpointCreateRequest,
    EndpointDeleteResponse,
    EndpointPatchRequest,
    EndpointResponse,
    ErrorResponse,
)
from backend.services.redaction import redact_text
from backend.services.url_security import validate_target_url

router = APIRouter()


def _response(endpoint: Endpoint) -> EndpointResponse:
    return EndpointResponse(
        id=endpoint.id,
        name=endpoint.name,
        url=redact_text(endpoint.url),
        service_key=endpoint.service_key,
        port=endpoint.port,
        probe_interval_seconds=endpoint.probe_interval_seconds,
        enabled=endpoint.enabled,
        is_demo_target=endpoint.is_demo_target,
        created_at=utc_iso(endpoint.created_at),
    )


def _interval_seconds(value: float | str | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, str):
        return float(value.removesuffix("s"))
    return float(value)


@router.get(
    "/endpoints",
    response_model=list[EndpointResponse],
)
def list_endpoints(db: Session = Depends(get_db)) -> list[EndpointResponse]:
    endpoints = db.scalars(select(Endpoint).order_by(Endpoint.id)).all()
    return [_response(endpoint) for endpoint in endpoints]


@router.post(
    "/endpoints",
    response_model=EndpointResponse,
    status_code=201,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def create_endpoint(
    payload: EndpointCreateRequest,
    db: Session = Depends(get_db),
) -> EndpointResponse:
    def ensure_capacity() -> None:
        endpoint_count = db.scalar(select(func.count(Endpoint.id))) or 0
        if endpoint_count >= 50:
            raise AppError(
                "ENDPOINT_LIMIT_REACHED",
                "The endpoint registry is limited to 50 endpoints.",
                409,
            )

    ensure_capacity()
    await validate_target_url(db, payload.url)
    ensure_capacity()
    parsed = urlsplit(payload.url)
    port = payload.port or parsed.port or (443 if parsed.scheme == "https" else 80)
    demo = db.scalar(
        select(Endpoint.id).where(
            Endpoint.service_key == (payload.service_key or payload.name.strip().lower()),
            Endpoint.port == port,
            Endpoint.is_demo_target.is_(True),
            Endpoint.enabled.is_(True),
        )
    )
    is_demo_target = bool(
        demo is not None
        and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
        and port in {5001, 5002, 5003}
    )
    endpoint = Endpoint(
        name=payload.name.strip(),
        url=payload.url,
        service_key=payload.service_key,
        port=port,
        probe_interval_seconds=_interval_seconds(payload.probe_interval_seconds) or 2.0,
        enabled=payload.enabled,
        is_demo_target=is_demo_target,
    )
    db.add(endpoint)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError("ENDPOINT_NAME_EXISTS", "An endpoint with this name already exists.", 409) from exc
    db.refresh(endpoint)
    return _response(endpoint)


@router.patch(
    "/endpoints/{endpoint_id}",
    response_model=EndpointResponse,
    responses={404: {"model": ErrorResponse}},
)
def patch_endpoint(
    endpoint_id: int,
    payload: EndpointPatchRequest,
    db: Session = Depends(get_db),
) -> EndpointResponse:
    endpoint = db.get(Endpoint, endpoint_id)
    if endpoint is None:
        raise AppError("ENDPOINT_NOT_FOUND", "Endpoint was not found.", 404)
    changes = payload.model_dump(exclude_unset=True)
    if "probe_interval_seconds" in changes and changes["probe_interval_seconds"] is not None:
        endpoint.probe_interval_seconds = _interval_seconds(changes["probe_interval_seconds"]) or 2.0
    if "enabled" in changes and changes["enabled"] is not None:
        endpoint.enabled = changes["enabled"]
    db.commit()
    db.refresh(endpoint)
    return _response(endpoint)


@router.delete(
    "/endpoints/{endpoint_id}",
    response_model=EndpointDeleteResponse,
    responses={404: {"model": ErrorResponse}},
)
def delete_endpoint(
    endpoint_id: int,
    db: Session = Depends(get_db),
) -> EndpointDeleteResponse:
    endpoint = db.get(Endpoint, endpoint_id)
    if endpoint is None:
        raise AppError("ENDPOINT_NOT_FOUND", "Endpoint was not found.", 404)
    if endpoint.is_demo_target:
        raise AppError("DEMO_ENDPOINT_PROTECTED", "Seeded demo endpoints cannot be deleted.", 403)
    db.execute(delete(ProbeResult).where(ProbeResult.endpoint_id == endpoint.id))
    db.delete(endpoint)
    db.commit()
    return EndpointDeleteResponse(deleted=True)
