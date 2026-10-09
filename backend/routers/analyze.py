from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import (
    AnalyzeIncidentRequest,
    AnalyzeIncidentResponse,
    ErrorResponse,
)
from backend.services.llm import analyze_incident as analyze_telemetry
from backend.services.pipeline import persist_analysis_incident

router = APIRouter()


@router.post(
    "/analyze",
    response_model=AnalyzeIncidentResponse,
    responses={422: {"model": ErrorResponse}},
)
async def analyze(
    request: AnalyzeIncidentRequest,
    db: Session = Depends(get_db),
) -> AnalyzeIncidentResponse:
    report = await analyze_telemetry(request.metrics, request.logs)
    incident = persist_analysis_incident(
        db,
        request.metrics,
        request.logs,
        report,
    )
    return AnalyzeIncidentResponse(**report, incident_id=incident.id)
