import hmac
import io
import secrets
import uuid
import warnings
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import APIKeyHeader
from PIL import Image, ImageOps
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.errors import AppError
from backend.models import EmergencyCase
from backend.schemas import (
    EmergencyEvidenceUploadResponse,
    EmergencyIntakeRequest,
    EmergencyIntakeResponse,
    ErrorResponse,
)
from backend.services.events import publish_event
from backend.services.llm.service import triage_emergency
from backend.services.redaction import redact_text

router = APIRouter()

MAX_EVIDENCE_BYTES = 5 * 1024 * 1024
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "uploads"
_MIME_FORMATS = {
    "image/png": ("PNG", "png"),
    "image/jpeg": ("JPEG", "jpg"),
    "image/webp": ("WEBP", "webp"),
}
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

def _new_case_id() -> str:
    return f"EMG-{uuid.uuid4().hex[:12].upper()}"

def _require_evidence_auth(api_key: Annotated[str | None, Depends(_API_KEY_HEADER)]) -> None:
    configured_key = settings.api_key
    if configured_key is None or not configured_key.get_secret_value().strip():
        raise AppError(
            "EVIDENCE_AUTH_NOT_CONFIGURED",
            "Evidence access is unavailable until API_KEY is configured.",
            503,
        )
    if api_key is None or not hmac.compare_digest(
        api_key,
        configured_key.get_secret_value(),
    ):
        raise AppError("UNAUTHORIZED", "A valid API key is required.", 401)


def _triage_summary(summary: str) -> str:
    return redact_text(summary)[:1000]


async def _validated_image(upload: UploadFile) -> tuple[bytes, str, str]:
    declared_type = upload.content_type or ""
    if declared_type not in _MIME_FORMATS:
        raise AppError(
            "UNSUPPORTED_EVIDENCE_TYPE",
            "Evidence must be a PNG, JPEG, or WebP image.",
            415,
        )

    content = await upload.read(MAX_EVIDENCE_BYTES + 1)
    if len(content) > MAX_EVIDENCE_BYTES:
        raise AppError("EVIDENCE_TOO_LARGE", "Evidence images may not exceed 5 MB.", 413)
    if not content:
        raise AppError("INVALID_EVIDENCE_IMAGE", "The uploaded file is not a valid image.", 415)

    expected_format, extension = _MIME_FORMATS[declared_type]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(content)) as image:
                actual_format = image.format
                image.verify()
            if actual_format != expected_format:
                raise ValueError("Image content does not match its declared type.")

            with Image.open(io.BytesIO(content)) as image:
                clean_image = ImageOps.exif_transpose(image)
                clean_image.load()
                mode = "RGBA" if "A" in clean_image.getbands() else "RGB"
                clean_image = clean_image.convert(mode)
                output = io.BytesIO()
                clean_image.save(output, format=expected_format, exif=b"")
    except (Image.DecompressionBombError, Image.DecompressionBombWarning, OSError, ValueError) as exc:
        raise AppError(
            "INVALID_EVIDENCE_IMAGE",
            "The uploaded file is not a valid supported image.",
            415,
        ) from exc

    return output.getvalue(), declared_type, extension


@router.post(
    "/emergency/intake",
    response_model=EmergencyIntakeResponse,
    status_code=201,
    responses={422: {"model": ErrorResponse}},
)
async def intake_emergency(
    payload: EmergencyIntakeRequest,
    db: Session = Depends(get_db),
) -> EmergencyIntakeResponse:
    triage = await triage_emergency(
        redact_text(payload.description),
        payload.priority,
    )
    summary = _triage_summary(triage["summary"])
    case = EmergencyCase(
        case_id=_new_case_id(db),
        incident_type=redact_text(payload.incident_type)[:200],
        location=redact_text(payload.location)[:300],
        priority=payload.priority,
        reported_by=redact_text(payload.reported_by)[:120],
        description=redact_text(payload.description)[:2000],
        status="Dispatched",
        ai_triage_summary=summary,
        llm_status=triage["llmStatus"],
    )
    db.add(case)
    db.commit()
    publish_event(
        case.case_id,
        "intake",
        case.status,
        details={
            "caseId": case.case_id,
            "priority": case.priority,
            "aiTriageSummary": case.ai_triage_summary,
        },
        event_type="incident_created",
    )
    return EmergencyIntakeResponse(
        case_id=case.case_id,
        status="Dispatched",
        ai_triage_summary=summary,
    )


@router.post(
    "/emergency/{case_id}/evidence",
    response_model=EmergencyEvidenceUploadResponse,
    status_code=201,
    responses={
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        413: {"model": ErrorResponse},
        415: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
async def upload_evidence(
    case_id: str,
    upload: Annotated[UploadFile, File()],
    db: Session = Depends(get_db),
    _authenticated: None = Depends(_require_evidence_auth),
) -> EmergencyEvidenceUploadResponse:
    case = db.scalar(select(EmergencyCase).where(EmergencyCase.case_id == case_id))
    if case is None:
        raise AppError("EMERGENCY_CASE_NOT_FOUND", "Emergency case was not found.", 404)
    if case.evidence_path is not None:
        raise AppError(
            "EVIDENCE_ALREADY_UPLOADED",
            "Evidence has already been uploaded for this case.",
            409,
        )

    content, content_type, extension = await _validated_image(upload)
    filename = f"{uuid.uuid4().hex}.{extension}"
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    destination = UPLOAD_ROOT / filename
    with destination.open("xb") as evidence_file:
        evidence_file.write(content)

    relative_path = (Path("uploads") / filename).as_posix()
    case.evidence_path = relative_path
    try:
        db.commit()
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise

    publish_event(
        case.case_id,
        "evidence",
        "uploaded",
        details={"caseId": case.case_id, "contentType": content_type},
        event_type="incident_created",
    )
    return EmergencyEvidenceUploadResponse(
        case_id=case.case_id,
        status="uploaded",
        content_type=content_type,
    )


@router.get(
    "/emergency/{case_id}/evidence",
    response_class=FileResponse,
    responses={
        200: {
            "content": {
                "image/png": {},
                "image/jpeg": {},
                "image/webp": {},
            },
            "headers": {
                "Content-Disposition": {"schema": {"type": "string"}},
                "X-Content-Type-Options": {"schema": {"type": "string"}},
            },
        },
        401: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)
def get_evidence(
    case_id: str,
    db: Session = Depends(get_db),
    _authenticated: None = Depends(_require_evidence_auth),
) -> FileResponse:
    case = db.scalar(select(EmergencyCase).where(EmergencyCase.case_id == case_id))
    if case is None or case.evidence_path is None:
        raise AppError("EVIDENCE_NOT_FOUND", "Evidence was not found.", 404)

    relative_path = Path(case.evidence_path)
    if relative_path.parts != ("uploads", relative_path.name):
        raise AppError("EVIDENCE_NOT_FOUND", "Evidence was not found.", 404)
    path = (UPLOAD_ROOT / relative_path.name).resolve()
    if path.parent != UPLOAD_ROOT.resolve() or not path.is_file():
        raise AppError("EVIDENCE_NOT_FOUND", "Evidence was not found.", 404)
    content_type = next(
        (mime for mime, (_, extension) in _MIME_FORMATS.items() if path.suffix == f".{extension}"),
        None,
    )
    if content_type is None:
        raise AppError("EVIDENCE_NOT_FOUND", "Evidence was not found.", 404)

    return FileResponse(
        path,
        media_type=content_type,
        filename=f"{case.case_id}-evidence{path.suffix}",
        content_disposition_type="attachment",
        headers={"X-Content-Type-Options": "nosniff"},
    )
