import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit, urlunsplit

import httpx

from backend.models import utc_now


@dataclass(frozen=True)
class Probe:
    http_status: int | None
    ping_latency_ms: float
    ok: bool
    checked_at: datetime
    cpu_percent: float | None = None
    ssl_cert_days: int | None = None


def health_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/healthz"):
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    if path not in {"", "/"}:
        return urlunsplit((parsed.scheme, parsed.netloc, path, parsed.query, parsed.fragment))
    return urlunsplit(
        (parsed.scheme, parsed.netloc, f"{path}/healthz", parsed.query, parsed.fragment)
    )


def metrics_url(base_url: str) -> str:
    parsed = urlsplit(base_url)
    path = parsed.path.rstrip("/")
    if path.endswith("/healthz"):
        path = path[: -len("/healthz")]
    return urlunsplit((parsed.scheme, parsed.netloc, f"{path}/_metrics", "", ""))


async def probe_endpoint(
    client: httpx.AsyncClient,
    url: str,
    *,
    read_cpu_metric: bool = False,
    timeout_seconds: float | None = None,
) -> Probe:
    checked_at = utc_now()
    started = time.perf_counter()
    status: int | None = None
    cpu_percent: float | None = None
    ssl_cert_days: int | None = None
    latency_ms: float | None = None
    request_options = {"timeout": timeout_seconds} if timeout_seconds is not None else {}
    try:
        response = await client.get(health_url(url), **request_options)
        status = response.status_code
        latency_ms = round((time.perf_counter() - started) * 1000, 3)
        if urlsplit(url).scheme.lower() == "https":
            try:
                stream = response.extensions.get("network_stream")
                ssl_object = stream.get_extra_info("ssl_object") if stream else None
                certificate = ssl_object.getpeercert() if ssl_object else {}
                expires = certificate.get("notAfter")
                if expires:
                    expires_at = datetime.strptime(expires, "%b %d %H:%M:%S %Y %Z").replace(
                        tzinfo=timezone.utc
                    )
                    remaining_days = (expires_at - datetime.now(timezone.utc)).total_seconds()
                    ssl_cert_days = max(0, int(remaining_days // 86400))
            except (AttributeError, OSError, TypeError, ValueError):
                ssl_cert_days = None
        if read_cpu_metric and 200 <= status < 300:
            try:
                metric_response = await client.get(metrics_url(url), **request_options)
                if metric_response.is_success:
                    payload = metric_response.json()
                    value = payload.get("cpuPercent") if isinstance(payload, dict) else None
                    if isinstance(value, (int, float)) and not isinstance(value, bool):
                        cpu_percent = float(value)
            except (httpx.HTTPError, ValueError):
                cpu_percent = None
        return Probe(
            http_status=status,
            ping_latency_ms=latency_ms,
            ok=200 <= status < 300,
            checked_at=checked_at,
            cpu_percent=cpu_percent,
            ssl_cert_days=ssl_cert_days,
        )
    except (httpx.HTTPError, ValueError):
        return Probe(
            http_status=status,
            ping_latency_ms=latency_ms or round((time.perf_counter() - started) * 1000, 3),
            ok=False,
            checked_at=checked_at,
            cpu_percent=cpu_percent,
            ssl_cert_days=ssl_cert_days,
        )
