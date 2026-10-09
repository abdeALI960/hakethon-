import json
import subprocess
import sys
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from backend.config import Settings, settings
from backend.errors import AppError
from backend.repositories.endpoints import is_registered_demo_target
from backend.services.redaction import redact_text


class DemoService(str, Enum):
    WEB = "web"
    API = "api"
    WORKER = "worker"


class ChaosAction(str, Enum):
    CRASH = "crash"
    CPU = "cpu"
    LATENCY = "latency"


class FixAction(str, Enum):
    RESTART = "restart"
    KILL_SPINLOOP = "kill_spinloop"
    CLEAR_LATENCY = "clear_latency"


_PORT_BY_SERVICE = {
    DemoService.WEB: 5001,
    DemoService.API: 5002,
    DemoService.WORKER: 5003,
}
_ROOT = Path(__file__).resolve().parents[2]
_SCRIPTS = _ROOT / "backend" / "scripts"
_MAX_OUTPUT = 2000


@dataclass(frozen=True)
class DemoTarget:
    service: DemoService
    port: int
    host: str = "127.0.0.1"

    def __post_init__(self) -> None:
        if type(self.service) is not DemoService:
            raise ValueError("service must be a DemoService enum")
        if type(self.port) is not int or self.port != _PORT_BY_SERVICE[self.service]:
            raise ValueError("service and port are not an allowed demo target")
        if self.host != "127.0.0.1":
            raise ValueError("demo targets must use 127.0.0.1")


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    new_pid: int | None
    stdout: str
    duration_sec: float


def _validate_target(target: DemoTarget) -> None:
    if type(target) is not DemoTarget:
        raise ValueError("target must be a validated DemoTarget")
    target.__post_init__()


def _run(script: Path, action: str, target: DemoTarget) -> ExecutionResult:
    started = time.perf_counter()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                action,
                "--target",
                f"{target.service.value}:{target.port}",
            ],
            shell=False,
            timeout=10,
            capture_output=True,
            text=True,
            cwd=_ROOT,
        )
        output = redact_text(completed.stdout or "")[:_MAX_OUTPUT]
        new_pid: int | None = None
        try:
            payload = json.loads(completed.stdout or "")
            pid = payload.get("new_pid")
            if isinstance(pid, int) and not isinstance(pid, bool) and pid > 0:
                new_pid = pid
        except (json.JSONDecodeError, AttributeError):
            pass
        return ExecutionResult(
            ok=completed.returncode == 0,
            new_pid=new_pid,
            stdout=output,
            duration_sec=round(time.perf_counter() - started, 3),
        )
    except (subprocess.TimeoutExpired, OSError):
        return ExecutionResult(
            ok=False,
            new_pid=None,
            stdout="Demo action failed or timed out.",
            duration_sec=round(time.perf_counter() - started, 3),
        )


async def execute_chaos(
    action: ChaosAction,
    target: DemoTarget,
    *,
    config: Settings | None = None,
) -> ExecutionResult:
    if type(action) is not ChaosAction:
        raise ValueError("action must be a ChaosAction enum")
    _validate_target(target)
    selected_settings = config or settings
    if not selected_settings.chaos_enabled:
        raise AppError("CHAOS_DISABLED", "Chaos injection is disabled.", 403)
    if action is ChaosAction.CPU and target.service is not DemoService.WORKER:
        raise ValueError("CPU chaos is allowed only for the worker demo target")
    if action is ChaosAction.LATENCY and target.service is not DemoService.WEB:
        raise ValueError("Latency chaos is allowed only for the web demo target")
    return await run_in_threadpool(_run, _SCRIPTS / "inject.py", action.value, target)


async def execute_fix(
    action: FixAction,
    target: DemoTarget,
    db: Session,
) -> ExecutionResult:
    if type(action) is not FixAction:
        raise ValueError("action must be a FixAction enum")
    _validate_target(target)
    registered = is_registered_demo_target(db, target.service.value, target.port)
    if not registered:
        raise AppError(
            "DEMO_TARGET_NOT_REGISTERED",
            "Fixes may only target a registered demo endpoint.",
            403,
        )
    if action is FixAction.KILL_SPINLOOP and target.service is not DemoService.WORKER:
        raise ValueError("kill_spinloop is allowed only for the worker demo target")
    if action is FixAction.CLEAR_LATENCY and target.service is not DemoService.WEB:
        raise ValueError("clear_latency is allowed only for the web demo target")
    return await run_in_threadpool(_run, _SCRIPTS / "fixer.py", action.value, target)
