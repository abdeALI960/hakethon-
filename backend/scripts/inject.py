import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Inject an allow-listed local demo failure.")
    parser.add_argument("action", choices=("crash", "cpu", "latency"))
    parser.add_argument("--target", required=True)
    args = parser.parse_args()
    try:
        target = parse_target(args.target)
        if args.action == "cpu":
            if target.service != "worker":
                raise ValueError("cpu injection is supported only on worker:5003")
            result = _control(target, "/_chaos/cpu?seconds=5")
        elif args.action == "latency":
            if target.service != "web":
                raise ValueError("latency injection is supported only on web:5001")
            result = _control(target, "/_chaos/latency")
        else:
            result = _control(target, "/_chaos/crash")
        print(json.dumps(result, separators=(",", ":")))
        return 0
    except (ValueError, urllib.error.URLError, TimeoutError, json.JSONDecodeError):
        print("Chaos injection failed or target was not allow-listed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
