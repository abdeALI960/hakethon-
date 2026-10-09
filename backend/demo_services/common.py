import asyncio
import ipaddress
import os
import threading
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request

_latency_enabled: dict[str, threading.Event] = {}
_cpu_stop: dict[str, threading.Event] = {}
_cpu_lock: dict[str, threading.Lock] = {}
_cpu_thread: dict[str, threading.Thread | None] = {}
_cpu_sample: dict[str, tuple[float, float] | None] = {}


def create_demo_app(service: str, port: int) -> FastAPI:
    app = FastAPI(title=f"OpsPilot demo {service}")
    latency = _latency_enabled.setdefault(service, threading.Event())
    cpu_stop = _cpu_stop.setdefault(service, threading.Event())
    cpu_lock = _cpu_lock.setdefault(service, threading.Lock())
    _cpu_thread.setdefault(service, None)
    _cpu_sample.setdefault(service, None)

    @app.middleware("http")
    async def apply_latency(request: Request, call_next: Any):
        if latency.is_set() and not request.url.path.startswith(("/_chaos/", "/_metrics")):
            await asyncio.sleep(5)
        return await call_next(request)

    def require_loopback(request: Request) -> None:
        host = request.client.host if request.client else ""
        try:
            is_loopback = ipaddress.ip_address(host).is_loopback
        except ValueError:
            is_loopback = False
        if not is_loopback:
            raise HTTPException(status_code=403, detail="Control endpoints are loopback-only")

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "service": service}

    @app.get("/_metrics")
    async def metrics() -> dict[str, float]:
        now_wall = time.perf_counter()
        now_cpu = time.process_time()
        previous = _cpu_sample[service]
        _cpu_sample[service] = (now_wall, now_cpu)
        cpu_percent = 0.0
        if previous is not None:
            elapsed_wall = now_wall - previous[0]
            elapsed_cpu = now_cpu - previous[1]
            if elapsed_wall > 0:
                cpu_percent = min(100.0, max(0.0, elapsed_cpu / elapsed_wall * 100.0))
        return {"cpuPercent": round(cpu_percent, 2)}

    @app.get("/")
    async def index() -> dict[str, Any]:
        return {"service": service, "port": port}

    @app.post("/_chaos/cpu", status_code=202)
    async def start_cpu(
        request: Request,
        seconds: int = Query(default=5, ge=1, le=8),
    ) -> dict[str, str | int]:
        require_loopback(request)
        with cpu_lock:
            thread = _cpu_thread[service]
            if thread is not None and thread.is_alive():
                return {"status": "already_running", "seconds": seconds}
            cpu_stop.clear()

            def consume_cpu() -> None:
                deadline = time.monotonic() + seconds
                value = 1
                while not cpu_stop.is_set() and time.monotonic() < deadline:
                    value = (value * 31 + 7) % 1_000_003

            thread = threading.Thread(
                target=consume_cpu,
                name=f"opspilot-{service}-cpu-chaos",
                daemon=True,
            )
            _cpu_thread[service] = thread
            thread.start()
        return {"status": "started", "seconds": seconds}

    @app.post("/_chaos/cpu/stop")
    async def stop_cpu(request: Request) -> dict[str, str]:
        require_loopback(request)
        cpu_stop.set()
        return {"status": "stopping"}

    @app.post("/_chaos/latency")
    async def enable_latency(request: Request) -> dict[str, str]:
        require_loopback(request)
        latency.set()
        return {"status": "enabled", "delaySeconds": "5"}

    @app.post("/_chaos/latency/clear")
    async def clear_latency(request: Request) -> dict[str, str]:
        require_loopback(request)
        latency.clear()
        return {"status": "cleared"}

    @app.post("/_chaos/crash")
    async def crash(request: Request) -> dict[str, str]:
        require_loopback(request)
        threading.Timer(0.2, os._exit, args=(1,)).start()
        return {"status": "crashing"}

    return app
