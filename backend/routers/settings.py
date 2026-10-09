from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import settings as app_settings
from backend.database import get_db
from backend.errors import AppError
from backend.models import RuntimeSettings
from backend.schemas import ErrorResponse, SettingsResponse, SettingsUpdateRequest
from backend.services.url_security import validate_target_url

router = APIRouter()


def _runtime_settings(db: Session) -> RuntimeSettings:
    row = db.get(RuntimeSettings, 1)
    if row is None:
        row = RuntimeSettings(
            id=1,
            llm_provider=app_settings.llm_provider,
            zero_touch_enabled=app_settings.zero_touch_default,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def _response(row: RuntimeSettings) -> SettingsResponse:
    return SettingsResponse(
        llm_provider=row.llm_provider,
        p99_latency_sla_ms=row.p99_latency_sla_ms,
        webhook_url=row.webhook_url,
        zero_touch_enabled=row.zero_touch_enabled,
        operator_name=row.operator_name,
    )


@router.get("/settings", response_model=SettingsResponse)
def get_settings(db: Session = Depends(get_db)) -> SettingsResponse:
    return _response(_runtime_settings(db))


@router.put(
    "/settings",
    response_model=SettingsResponse,
    responses={403: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def update_settings(
    payload: SettingsUpdateRequest,
    db: Session = Depends(get_db),
) -> SettingsResponse:
    if payload.webhook_url is not None:
        await validate_target_url(
            db,
            payload.webhook_url,
            https_only=True,
            allow_registered=False,
        )
    row = _runtime_settings(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return _response(row)
