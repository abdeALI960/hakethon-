import asyncio
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from sqlalchemy import delete, select

from backend.database import SessionLocal
from backend.models import Endpoint, ProbeResult, RuntimeSettings
from backend.services.events import publish_event
from backend.services.pipeline import process_detected_anomaly
from backend.services.probe import Probe, probe_endpoint

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class _EndpointConfig:
    id: int
    name: str
    url: str
    service_key: str | None
    port: int | None
    probe_interval_seconds: float
    is_demo_target: bool


def _classify_anomaly(
    probe: Probe,
    sla_ms: float,
    consecutive_slow_probes: int,
) -> str | None:
    if not probe.ok:
        return "CRASH"
    if probe.cpu_percent is not None and probe.cpu_percent > 90:
        return "CPU_SPIKE"
    if probe.ping_latency_ms > sla_ms and consecutive_slow_probes >= 2:
        return "LATENCY"
    return None


def _load_monitor_state() -> tuple[list[_EndpointConfig], float]:
    with SessionLocal() as db:
        endpoints = db.scalars(select(Endpoint).where(Endpoint.enabled.is_(True))).all()
        endpoint_configs = [
            _EndpointConfig(
                id=endpoint.id,
                name=endpoint.name,
                url=endpoint.url,
                service_key=endpoint.service_key,
                port=endpoint.port,
                probe_interval_seconds=endpoint.probe_interval_seconds,
                is_demo_target=endpoint.is_demo_target,
            )
            for endpoint in endpoints
        ]
        runtime = db.get(RuntimeSettings, 1)
        sla_ms = runtime.p99_latency_sla_ms if runtime is not None else 1000.0
    return endpoint_configs, sla_ms


def _store_probe(endpoint_id: int, probe: Probe) -> None:
    with SessionLocal() as db:
        db.add(
            ProbeResult(
                endpoint_id=endpoint_id,
                http_status=probe.http_status,
                ping_latency_ms=probe.ping_latency_ms,
                ssl_cert_days=probe.ssl_cert_days,
                ok=probe.ok,
                checked_at=probe.checked_at,
            )
        )
        db.flush()
        keep_ids = (
            select(ProbeResult.id)
            .where(ProbeResult.endpoint_id == endpoint_id)
            .order_by(ProbeResult.checked_at.desc(), ProbeResult.id.desc())
            .limit(1000)
        )
        db.execute(
            delete(ProbeResult).where(
                ProbeResult.endpoint_id == endpoint_id,
                ProbeResult.id.not_in(keep_ids),
            )
        )
        db.commit()
    publish_event(
        None,
        "probe",
        "healthy" if probe.ok else "failed",
        endpoint_id=endpoint_id,
        timestamp=probe.checked_at,
        details={
            "httpStatus": probe.http_status,
            "pingLatencyMs": probe.ping_latency_ms,
            "sslCertDays": probe.ssl_cert_days,
        },
        event_type="probe_result",
    )


async def _handle_anomaly(
    endpoint_config: _EndpointConfig,
    anomaly_type: str,
    probe: Probe,
) -> None:
    try:
        with SessionLocal() as db:
            endpoint = db.get(Endpoint, endpoint_config.id)
            if endpoint is None:
                return
            logs = [
                (
                    f"Probe failed with HTTP status {probe.http_status}."
                    if probe.http_status is not None
                    else "Probe failed because the endpoint could not be reached."
                )
            ]
            if probe.cpu_percent is not None:
                logs.append(f"Demo process CPU utilization: {probe.cpu_percent:.2f}%.")
            metrics: dict[str, Any] = {
                "anomaly_type": anomaly_type,
                "ping_latency_ms": probe.ping_latency_ms,
                "http_status": probe.http_status,
                "cpu_percent": probe.cpu_percent,
            }
            await process_detected_anomaly(
                db,
                endpoint,
                anomaly_type,
                metrics=metrics,
                logs=logs,
            )
    except Exception:
        logger.error("Could not process anomaly for endpoint %s.", endpoint_config.id)


async def monitor_loop() -> None:
    """Probe enabled endpoints until cancelled, isolating failures per endpoint."""
    next_probe_at: dict[int, float] = {}
    slow_probe_counts: dict[int, int] = {}
    active_incidents: set[int] = set()
    processing_tasks: set[asyncio.Task[None]] = set()
    timeout = httpx.Timeout(2)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            while True:
                try:
                    endpoints, sla_ms = _load_monitor_state()
                    active_ids = {endpoint.id for endpoint in endpoints}
                    for removed_id in set(next_probe_at) - active_ids:
                        next_probe_at.pop(removed_id, None)
                        slow_probe_counts.pop(removed_id, None)
                        active_incidents.discard(removed_id)

                    now = asyncio.get_running_loop().time()
                    due = [
                        endpoint
                        for endpoint in endpoints
                        if now >= next_probe_at.get(endpoint.id, 0)
                    ]
                    results = await asyncio.gather(
                        *(
                            probe_endpoint(
                                client,
                                endpoint.url,
                                read_cpu_metric=endpoint.is_demo_target,
                            )
                            for endpoint in due
                        ),
                        return_exceptions=True,
                    )
                    for endpoint, result in zip(due, results, strict=True):
                        interval = max(0.1, endpoint.probe_interval_seconds)
                        next_probe_at[endpoint.id] = now + interval
                        if isinstance(result, BaseException):
                            logger.error("Probe worker failed for endpoint %s.", endpoint.id)
                            continue
                        probe = result
                        try:
                            _store_probe(endpoint.id, probe)
                        except Exception:
                            logger.error("Could not persist probe for endpoint %s.", endpoint.id)
                            continue
                        if probe.ok:
                            if probe.ping_latency_ms > sla_ms:
                                slow_probe_counts[endpoint.id] = (
                                    slow_probe_counts.get(endpoint.id, 0) + 1
                                )
                            else:
                                slow_probe_counts[endpoint.id] = 0
                            anomaly = _classify_anomaly(
                                probe,
                                sla_ms,
                                slow_probe_counts[endpoint.id],
                            )
                        else:
                            slow_probe_counts[endpoint.id] = 0
                            anomaly = "CRASH"
                        if anomaly is None:
                            active_incidents.discard(endpoint.id)
                        elif endpoint.id not in active_incidents:
                            active_incidents.add(endpoint.id)
                            task = asyncio.create_task(
                                _handle_anomaly(endpoint, anomaly, probe)
                            )
                            processing_tasks.add(task)
                            task.add_done_callback(processing_tasks.discard)

                    next_due = min(next_probe_at.values(), default=now + 1)
                    await asyncio.sleep(max(0.05, min(1.0, next_due - now)))
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.error("Monitor cycle failed; the next cycle will retry.")
                    await asyncio.sleep(1)
    finally:
        if processing_tasks:
            await asyncio.gather(*processing_tasks, return_exceptions=True)
