import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_PID_FILE = _ROOT / ".opspilot-demo-pids.json"
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.demo_services.targets import AllowedDemoTarget, parse_target


def _control(target: AllowedDemoTarget, path: str, timeout: float = 3) -> dict[str, object]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{target.port}{path}",
        data=b"",
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("invalid control response")
    return value


def _health(target: AllowedDemoTarget) -> bool:
    request = urllib.request.Request(f"http://127.0.0.1:{target.port}/healthz")
    try:
        with urllib.request.urlopen(request, timeout=0.5) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError):
        return False


def _new_pid(target: AllowedDemoTarget) -> int | None:
    try:
        pids = json.loads(_PID_FILE.read_text(encoding="utf-8"))
        entry = pids.get(target.service, {})
        pid = entry.get("pid")
        if (
            entry.get("port") == target.port
            and isinstance(pid, int)
            and not isinstance(pid, bool)
            and pid > 0
        ):
            return pid
    except (OSError, json.JSONDecodeError, AttributeError):
        return None
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply an allow-listed local demo fix.")
    parser.add_argument("action", choices=("restart", "kill_spinloop", "clear_latency"))
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        target = parse_target(args.target)
        if args.action == "kill_spinloop":
            if target.service != "worker":
                raise ValueError("kill_spinloop is supported only on worker:5003")
            result = _control(target, "/_chaos/cpu/stop")
        elif args.action == "clear_latency":
            if target.service != "web":
                raise ValueError("clear_latency is supported only on web:5001")
            result = _control(target, "/_chaos/latency/clear")
        else:
            previous_pid = _new_pid(target)
            try:
                _control(target, "/_chaos/crash")
            except (urllib.error.URLError, TimeoutError):
                pass
            deadline = time.monotonic() + 6.5
            new_pid = _new_pid(target)
            while time.monotonic() < deadline and (
                new_pid is None or new_pid == previous_pid or not _health(target)
            ):
                time.sleep(0.2)
                new_pid = _new_pid(target)
            if new_pid is None or new_pid == previous_pid or not _health(target):
                raise RuntimeError("supervisor did not restart demo target")
            result = {"status": "restarted", "new_pid": new_pid}
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (
        ValueError,
        RuntimeError,
        urllib.error.URLError,
        TimeoutError,
        json.JSONDecodeError,
    ):
        print("Fix failed or target was not an allow-listed registered demo.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
