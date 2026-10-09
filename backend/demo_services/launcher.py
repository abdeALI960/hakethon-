import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PID_FILE = _ROOT / ".opspilot-demo-pids.json"
_SERVICES = {
    "web": ("backend.demo_services.web:app", 5001),
    "api": ("backend.demo_services.api:app", 5002),
    "worker": ("backend.demo_services.worker:app", 5003),
}
_RESTART_DELAY_SECONDS = 2.5
_stopping = False


def _write_pids(processes: dict[str, subprocess.Popen[bytes]]) -> None:
    payload = {
        service: {"pid": process.pid, "port": _SERVICES[service][1]}
        for service, process in processes.items()
        if process.poll() is None
    }
    temporary = _PID_FILE.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(temporary, _PID_FILE)


def _stop(_signum: int, _frame: object) -> None:
    global _stopping
    _stopping = True


def main() -> None:
    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    processes: dict[str, subprocess.Popen[bytes]] = {}
    restart_at: dict[str, float] = {}
    try:
        while not _stopping:
            for service, (module, port) in _SERVICES.items():
                process = processes.get(service)
                if process is not None and process.poll() is not None:
                    restart_at.setdefault(
                        service,
                        time.monotonic() + _RESTART_DELAY_SECONDS,
                    )
                    if time.monotonic() < restart_at[service]:
                        continue
                elif process is not None:
                    continue
                processes[service] = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "uvicorn",
                        module,
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(port),
                    ],
                    cwd=_ROOT,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                restart_at.pop(service, None)
                print(f"Started {service} on 127.0.0.1:{port}", flush=True)
            _write_pids(processes)
            time.sleep(0.25)
    finally:
        for process in processes.values():
            if process.poll() is None:
                process.terminate()
        for process in processes.values():
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        _PID_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
