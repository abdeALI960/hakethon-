import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import SessionLocal
from backend.errors import AppError
from backend.models import (
    Analysis,
    Endpoint,
    Incident,
    IncidentLog,
    ProbeResult,
    Remediation,
    RuntimeSettings,
    utc_now,
)
from backend.services.events import publish_event, publish_log_event
from backend.services.executor import (
    DemoService,
    DemoTarget,
    ExecutionResult,
    FixAction,
    execute_fix,
)
from backend.services.llm import analyze_incident
from backend.services.probe import probe_endpoint
from backend.services.redaction import redact_logs, redact_text

logger = logging.getLogger(__name__)
ACTION_BY_ANOMALY = {
    "CRASH": FixAction.RESTART,
    "CPU_SPIKE": FixAction.KILL_SPINLOOP,
    "LATENCY": FixAction.CLEAR_LATENCY,
    "OTHER": None,
}
_ACTIVE_STATUSES = (
    "injected",
    "detected",
    "diagnosed",
    "fixed",
    "awaiting_approval",
)
_webhook_tasks: set[asyncio.Task[None]] = set()


@dataclass(frozen=True)
class _FastPathResult:
    execution: ExecutionResult
    verified: bool
    probes: list[ProbeResult]
    fixed_at: datetime | None
    verified_at: datetime | None
    duration_sec: float


def _next_incident_id(db: Session) -> str:
    ids = db.scalars(select(Incident.id)).all()
    sequence = 104
    for incident_id in ids:
        if incident_id.startswith("INC-"):
            try:
                sequence = max(sequence, int(incident_id[4:]))
            except ValueError:
                continue
    return f"INC-{sequence + 1}"


def create_injected_incident(
    db: Session,
    endpoint: Endpoint,
    anomaly_type: str,
) -> Incident:
    now = utc_now()
    incident = _find_active_incident(db, endpoint)
    if incident is None:
        incident = Incident(
            id=_next_incident_id(db),
            service=endpoint.service_key or endpoint.name,
            port=endpoint.port,
            anomaly_type=anomaly_type,
            severity="CRIT" if anomaly_type in {"CRASH", "CPU_SPIKE"} else "WARN",
            status="injected",
            auto_healed=False,
            injected_at=now,
            created_at=now,
        )
        db.add(incident)
        db.flush()
        _add_log(
            db,
            incident.id,
            incident.severity,
            f"{anomaly_type} injected for {incident.service}.",
            timestamp=now,
        )
    else:
        incident.anomaly_type = anomaly_type
        incident.injected_at = incident.injected_at or now
        if incident.detected_at is None:
            incident.status = "injected"
        _add_log(
            db,
            incident.id,
            incident.severity,
            f"{anomaly_type} injection requested for {incident.service}.",
            timestamp=now,
        )
    db.commit()
    publish_event(incident.id, "injected", incident.status, timestamp=incident.injected_at)
    return incident


def persist_analysis_incident(
    db: Session,
    metrics: dict[str, Any],
    logs: list[str],
    report: dict[str, Any],
) -> Incident:
    now = utc_now()
    action = str(report.get("recommendedAction", "none"))
    anomaly_type = {
        "restart": "CRASH",
        "kill_spinloop": "CPU_SPIKE",
        "clear_latency": "LATENCY",
    }.get(action, "OTHER")
    service_value = metrics.get("service") or metrics.get("service_name") or metrics.get("serviceName")
    service = redact_text(service_value or "unknown")[:80]
    port_value = metrics.get("port")
    port = (
        int(port_value)
        if isinstance(port_value, int) and not isinstance(port_value, bool) and 1 <= port_value <= 65535
        else None
    )
    incident = Incident(
        id=_next_incident_id(db),
        service=service,
        port=port,
        anomaly_type=anomaly_type,
        severity="CRIT" if report.get("severity") == "CRIT" else "WARN",
        status="diagnosed",
        auto_healed=False,
        detected_at=now,
        diagnosed_at=now,
        created_at=now,
    )
    db.add(incident)
    db.flush()
    _add_log(db, incident.id, "INFO", f"Analysis requested for {service}.", timestamp=now)
    for log in redact_logs(logs):
        _add_log(db, incident.id, "INFO", log)
    safe_report = {
        **report,
        "summary": redact_text(report.get("summary", "")),
        "rootCause": redact_text(report.get("rootCause", "")),
        "rationale": redact_text(report.get("rationale", "")),
        "evidence": [redact_text(item) for item in report.get("evidence", [])],
    }
    db.add(
        Analysis(
            incident_id=incident.id,
            provider=settings.llm_provider,
            model=settings.llm_model or "unconfigured",
            llm_status=str(safe_report.get("llmStatus", "failed")),
            root_cause=safe_report["rootCause"][:2000],
            confidence=safe_report.get("confidence"),
            recommended_action=action,
            rationale=safe_report["rationale"][:2000] or "No rationale returned.",
            raw_report=safe_report,
            latency_ms=float(safe_report.get("latencyMs", 0)),
            created_at=now,
        )
    )
    db.add(
        Remediation(
            incident_id=incident.id,
            action=action,
            executed_by="auto",
            status="proposed",
            new_pid=None,
            probe_verified=False,
            fix_duration_sec=0,
            created_at=now,
        )
    )
    db.commit()
    publish_event(incident.id, "diagnosed", incident.status, timestamp=now)
    return incident


def _add_log(
    db: Session,
    incident_id: str,
    level: str,
    message: str,
    *,
    timestamp: datetime | None = None,
) -> None:
    safe_message = redact_text(message)[:2000]
    logged_at = timestamp or utc_now()
    db.add(
        IncidentLog(
            incident_id=incident_id,
            level=level,
            message=safe_message,
            ts=logged_at,
        )
    )
    publish_log_event(incident_id, logged_at, level, safe_message)


def _find_active_incident(db: Session, endpoint: Endpoint) -> Incident | None:
    return db.scalar(
        select(Incident)
        .where(
            Incident.service == (endpoint.service_key or endpoint.name),
            Incident.port == endpoint.port,
            Incident.status.in_(_ACTIVE_STATUSES),
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
    )


def _runtime_settings(db: Session) -> RuntimeSettings:
    row = db.get(RuntimeSettings, 1)
    if row is None:
        row = RuntimeSettings(
            id=1,
            llm_provider=settings.llm_provider,
            zero_touch_enabled=settings.zero_touch_default,
        )
        db.add(row)
        db.commit()
    return row


def _demo_target(endpoint: Endpoint) -> DemoTarget | None:
    if not endpoint.is_demo_target or endpoint.port is None:
        return None
    try:
        service = DemoService(endpoint.service_key or "")
        return DemoTarget(service, endpoint.port)
    except ValueError:
        return None


def _allowed_for_target(action: FixAction | None, target: DemoTarget | None) -> bool:
    if action is None or target is None:
        return False
    if action is FixAction.KILL_SPINLOOP:
        return target.service is DemoService.WORKER
    if action is FixAction.CLEAR_LATENCY:
        return target.service is DemoService.WEB
    return action is FixAction.RESTART


async def _execute_registered_fix(action: FixAction, target: DemoTarget) -> ExecutionResult:
    with SessionLocal() as execution_db:
        return await execute_fix(action, target, execution_db)


async def _verify_recovery(endpoint: Endpoint) -> tuple[bool, list[ProbeResult]]:
    recorded_probes: list[ProbeResult] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 10
    async with httpx.AsyncClient(timeout=2, follow_redirects=False) as client:
        while loop.time() < deadline:
            remaining = deadline - loop.time()
            probe = await probe_endpoint(
                client,
                endpoint.url,
                timeout_seconds=min(2, remaining),
            )
            recorded_probes.append(
                ProbeResult(
                    endpoint_id=endpoint.id,
                    http_status=probe.http_status,
                    ping_latency_ms=probe.ping_latency_ms,
                    ssl_cert_days=probe.ssl_cert_days,
                    ok=probe.ok,
                    checked_at=probe.checked_at,
                )
            )
            if probe.ok:
                return True, recorded_probes
            await asyncio.sleep(min(0.5, max(0, deadline - loop.time())))
    return False, recorded_probes


async def _execute_and_verify(
    action: FixAction,
    target: DemoTarget,
    endpoint: Endpoint,
) -> _FastPathResult:
    started = time.perf_counter()
    execution = await _execute_registered_fix(action, target)
    if not execution.ok:
        return _FastPathResult(
            execution=execution,
            verified=False,
            probes=[],
            fixed_at=None,
            verified_at=None,
            duration_sec=round(time.perf_counter() - started, 3),
        )
    fixed_at = utc_now()
    verified, probes = await _verify_recovery(endpoint)
    return _FastPathResult(
        execution=execution,
        verified=verified,
        probes=probes,
        fixed_at=fixed_at,
        verified_at=utc_now() if verified else None,
        duration_sec=round(time.perf_counter() - started, 3),
    )


async def _post_webhook(url: str, summary: dict[str, Any], incident_id: str) -> None:
    delivered = False
    try:
        async with httpx.AsyncClient(timeout=3, follow_redirects=False) as client:
            response = await client.post(url, json=summary)
            response.raise_for_status()
        delivered = True
    except (httpx.HTTPError, ValueError):
        logger.warning("Incident webhook delivery failed.")
    try:
        with SessionLocal() as db:
            incident = db.get(Incident, incident_id)
            if incident is None:
                return
            if delivered:
                _add_log(db, incident.id, "INFO", "Failure webhook delivered.")
                event_status = "delivered"
            else:
                _add_log(db, incident.id, "WARN", "Failure webhook delivery failed.")
                event_status = "failed"
            db.commit()
            publish_event(incident.id, "webhook", event_status)
    except Exception:
        logger.error("Could not persist incident webhook outcome.")


def _fire_webhook(db: Session, incident: Incident) -> None:
    row = _runtime_settings(db)
    url = row.webhook_url
    if not url:
        return
    summary = {
        "incidentId": incident.id,
        "service": redact_text(incident.service),
        "anomalyType": incident.anomaly_type,
        "status": incident.status,
        "summary": redact_text(
            f"{incident.anomaly_type} remediation for {incident.service} could not be verified."
        ),
    }
    task = asyncio.create_task(_post_webhook(url, summary, incident.id))
    _webhook_tasks.add(task)
    task.add_done_callback(_webhook_tasks.discard)


async def _diagnose(
    metrics: dict[str, Any],
    logs: list[str],
) -> dict[str, Any]:
    return await analyze_incident(metrics, redact_logs(logs))


async def process_detected_anomaly(
    db: Session,
    endpoint: Endpoint,
    anomaly_type: str,
    *,
    metrics: dict[str, Any] | None = None,
    logs: list[str] | None = None,
    incident_id: str | None = None,
) -> Incident | None:
    """Detect, diagnose, and optionally remediate one debounced endpoint incident."""
    current_stage = "detected"
    try:
        created = False
        incident = db.get(Incident, incident_id) if incident_id else None
        if incident is None:
            incident = _find_active_incident(db, endpoint)
        if incident is None:
            now = utc_now()
            incident = Incident(
                id=_next_incident_id(db),
                service=endpoint.service_key or endpoint.name,
                port=endpoint.port,
                anomaly_type=anomaly_type,
                severity="CRIT" if anomaly_type in {"CRASH", "CPU_SPIKE"} else "WARN",
                status="detected",
                auto_healed=False,
                detected_at=now,
                created_at=now,
            )
            db.add(incident)
            db.flush()
            created = True
            _add_log(
                db,
                incident.id,
                incident.severity,
                f"{anomaly_type} detected for {incident.service}.",
            )
        elif incident.detected_at is None:
            incident.detected_at = utc_now()
            incident.status = "detected"
            _add_log(
                db,
                incident.id,
                incident.severity,
                f"{anomaly_type} detected for {incident.service}.",
            )
        else:
            return incident
        if metrics is not None and metrics.get("injected") is True and incident.injected_at is None:
            incident.injected_at = incident.created_at
        incident.anomaly_type = anomaly_type
        db.commit()
        if created:
            publish_event(
                incident.id,
                "created",
                incident.status,
                timestamp=incident.created_at,
                event_type="incident_created",
            )
        publish_event(
            incident.id,
            "detected",
            incident.status,
            timestamp=incident.detected_at,
        )

        current_stage = "diagnosed"
        action = ACTION_BY_ANOMALY.get(anomaly_type)
        incident.diagnosed_at = utc_now()
        incident.status = "diagnosed"
        _add_log(
            db,
            incident.id,
            "INFO",
            f"Rule-based diagnosis recommends {action.value if action else 'none'}.",
        )
        runtime = _runtime_settings(db)
        db.commit()
        publish_event(
            incident.id,
            "diagnosed",
            incident.status,
            details={"recommendedAction": action.value if action else "none"},
            timestamp=incident.diagnosed_at,
        )

        safe_metrics = dict(metrics or {})
        safe_metrics["anomaly_type"] = anomaly_type
        safe_logs = redact_logs(logs or [])
        target = _demo_target(endpoint)
        automatic = runtime.zero_touch_enabled and _allowed_for_target(action, target)
        fix_task = (
            _execute_and_verify(action, target, endpoint)
            if automatic and action is not None and target is not None
            else None
        )
        tasks = [_diagnose(safe_metrics, safe_logs)]
        if fix_task is not None:
            tasks.insert(0, fix_task)
        results = await asyncio.gather(*tasks, return_exceptions=True)

        fast_path: _FastPathResult | None = None
        diagnosis: dict[str, Any]
        if fix_task is not None:
            if isinstance(results[0], Exception):
                fix_error: Exception | None = results[0]
                logger.error("Incident remediation executor failed for %s.", incident.id)
                _add_log(db, incident.id, "FIX", "Remediation executor failed.")
            else:
                fast_path = results[0]
                fix_error = None
        else:
            fix_error = None
        diagnosis_index = 1 if fix_task is not None else 0
        diagnosis_result = results[diagnosis_index]
        if isinstance(diagnosis_result, Exception):
            logger.error("LLM diagnosis failed unexpectedly for %s.", incident.id)
            diagnosis = {
                "rootCause": f"Rule-based anomaly classification: {anomaly_type}.",
                "confidence": 0.5,
                "severity": incident.severity,
                "recommendedAction": action.value if action else "none",
                "rationale": "Diagnosis service failed; action is based on rule-based telemetry.",
                "llmStatus": "failed",
                "latencyMs": 0,
                "llmError": "LLM_UNAVAILABLE",
            }
            _add_log(db, incident.id, "WARN", "LLM diagnosis failed; using rule-based diagnosis.")
        else:
            diagnosis = diagnosis_result
        diagnosis = {
            **diagnosis,
            "rootCause": redact_text(diagnosis.get("rootCause", "")),
            "rationale": redact_text(diagnosis.get("rationale", "")),
            "recommendedAction": action.value if action else "none",
            "latencyMs": diagnosis.get("latencyMs", 0),
        }
        db.add(
            Analysis(
                incident_id=incident.id,
                provider=settings.llm_provider,
                model=settings.llm_model or "unconfigured",
                llm_status=diagnosis.get("llmStatus", "failed"),
                root_cause=diagnosis["rootCause"][:2000],
                confidence=diagnosis.get("confidence"),
                recommended_action=diagnosis["recommendedAction"],
                rationale=diagnosis["rationale"][:2000] or "No rationale returned.",
                raw_report=diagnosis,
                latency_ms=float(diagnosis["latencyMs"] or 0),
                created_at=utc_now(),
            )
        )
        if diagnosis.get("llmError"):
            _add_log(db, incident.id, "WARN", f"LLM diagnosis fallback: {diagnosis['llmError']}.")

        current_stage = "fixed"
        if not automatic:
            incident.status = "awaiting_approval"
            _add_log(db, incident.id, "INFO", "Awaiting operator remediation approval.")
            db.commit()
            publish_event(incident.id, "awaiting_approval", incident.status)
            return incident

        if fix_error is not None or fast_path is None or not fast_path.execution.ok:
            incident.status = "failed"
            incident.auto_healed = False
            _add_log(db, incident.id, "FIX", "Remediation command failed.")
            db.add(
                Remediation(
                    incident_id=incident.id,
                    action=action.value if action else "none",
                    executed_by="auto",
                    status="failed",
                    new_pid=None,
                    probe_verified=False,
                    fix_duration_sec=fast_path.duration_sec if fast_path else 0,
                )
            )
            db.commit()
            publish_event(incident.id, "fixed", incident.status)
            _fire_webhook(db, incident)
            return incident

        if fast_path.fixed_at is None:
            raise RuntimeError("Successful remediation is missing its completion time.")
        incident.fixed_at = fast_path.fixed_at
        incident.status = "fixed" if fast_path.verified else "failed"
        incident.auto_healed = fast_path.verified
        if fast_path.verified:
            incident.verified_at = fast_path.verified_at
            incident.status = "verified"
            _add_log(db, incident.id, "FIX", f"Automatically executed {action.value}.")
            _add_log(db, incident.id, "INFO", "Recovery verified by a healthy probe.")
        else:
            _add_log(db, incident.id, "CRIT", "Recovery verification failed after 10 seconds.")
        db.add_all(fast_path.probes)
        db.add(
            Remediation(
                incident_id=incident.id,
                action=action.value,
                executed_by="auto",
                status=incident.status,
                new_pid=fast_path.execution.new_pid,
                probe_verified=fast_path.verified,
                fix_duration_sec=fast_path.duration_sec,
                created_at=incident.fixed_at,
            )
        )
        db.commit()
        publish_event(
            incident.id,
            "fixed",
            "fixed" if fast_path.verified else "failed",
            timestamp=incident.fixed_at,
        )
        publish_event(
            incident.id,
            "verified",
            incident.status,
            timestamp=fast_path.verified_at or utc_now(),
        )
        if not fast_path.verified:
            _fire_webhook(db, incident)
        return incident
    except Exception:
        logger.error("Incident pipeline failed during %s.", current_stage)
        try:
            db.rollback()
            failed = db.get(Incident, incident_id) if incident_id else None
            if failed is None:
                failed = _find_active_incident(db, endpoint)
            if failed is not None:
                failed.status = "failed"
                failed.auto_healed = False
                _add_log(
                    db,
                    failed.id,
                    "CRIT",
                    f"Pipeline stage {current_stage} failed; operator attention is required.",
                )
                db.commit()
                publish_event(failed.id, current_stage, "failed")
                _fire_webhook(db, failed)
        except Exception:
            db.rollback()
            logger.error("Could not persist incident pipeline failure.")
        return None


async def remediate_incident(
    db: Session,
    incident: Incident,
    endpoint: Endpoint,
    action: FixAction,
) -> Incident:
    """Execute an operator-approved fix and persist fixed/verified timestamps."""
    target = _demo_target(endpoint)
    if target is None or not _allowed_for_target(action, target):
        raise AppError(
            "INVALID_REMEDIATION_ACTION",
            "Action is not allowed for this registered demo endpoint.",
            400,
        )
    started = time.perf_counter()
    try:
        incident.status = "diagnosed"
        incident.diagnosed_at = incident.diagnosed_at or utc_now()
        _add_log(db, incident.id, "INFO", f"Operator approved {action.value}.")
        db.commit()
        publish_event(incident.id, "diagnosed", incident.status, timestamp=incident.diagnosed_at)
        result = await _execute_registered_fix(action, target)
        if not result.ok:
            raise RuntimeError("Remediation command failed.")
        incident.fixed_at = utc_now()
        incident.status = "fixed"
        db.commit()
        publish_event(
            incident.id,
            "fixed",
            incident.status,
            timestamp=incident.fixed_at,
        )
        verified, probes = await _verify_recovery(endpoint)
        db.add_all(probes)
        incident.status = "fixed" if verified else "failed"
        incident.auto_healed = False
        if verified:
            incident.verified_at = utc_now()
            incident.status = "verified"
            _add_log(db, incident.id, "FIX", f"Operator executed {action.value}.")
            _add_log(db, incident.id, "INFO", "Recovery verified by a healthy probe.")
        else:
            _add_log(db, incident.id, "CRIT", "Recovery verification failed after 10 seconds.")
        db.add(
            Remediation(
                incident_id=incident.id,
                action=action.value,
                executed_by="human",
                status=incident.status,
                new_pid=result.new_pid,
                probe_verified=verified,
                fix_duration_sec=round(time.perf_counter() - started, 3),
            )
        )
        db.commit()
        publish_event(
            incident.id,
            "verified" if verified else "fixed",
            incident.status,
            timestamp=incident.verified_at or incident.fixed_at,
        )
        if not verified:
            _fire_webhook(db, incident)
        return incident
    except Exception:
        db.rollback()
        incident.status = "failed"
        incident.auto_healed = False
        _add_log(db, incident.id, "CRIT", "Operator remediation failed; operator attention is required.")
        db.add(
            Remediation(
                incident_id=incident.id,
                action=action.value,
                executed_by="human",
                status="failed",
                probe_verified=False,
                fix_duration_sec=round(time.perf_counter() - started, 3),
            )
        )
        db.commit()
        publish_event(incident.id, "fixed", "failed")
        _fire_webhook(db, incident)
        return incident
