#!/usr/bin/env python3
"""Exercise the running OpsPilot stack using only its public HTTP API."""

from __future__ import annotations

import argparse
from datetime import datetime
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.schemas import (  # noqa: E402
    ChaosInjectionResponse,
    DbExportResponse,
    DbSchemaResponse,
    DbTableInfo,
    DbTableRowsResponse,
    DbTablesResponse,
    EmergencyEvidenceUploadResponse,
    EmergencyIntakeResponse,
    EndpointCreateRequest,
    EndpointDeleteResponse,
    EndpointResponse,
    HealthResponse,
    IncidentListResponse,
    IncidentResponse,
    KpiResponse,
    ProbeResponse,
    RemediationResponse,
    ServiceHealth,
    SettingsResponse,
    StreamEvent,
)

TYPE_SCRIPT_INTERFACES: dict[str, tuple[Path, str]] = {
    "HealthResponse": (ROOT / "src/services/apiClient.ts", "HealthResponse"),
    "ProbeResponse": (ROOT / "src/types/index.ts", "ProbeResponse"),
    "ChaosInjectionResponse": (ROOT / "src/types/index.ts", "ChaosInjectionResponse"),
    "RemediationResponse": (ROOT / "src/types/index.ts", "RemediationResponse"),
    "EmergencyIntakeResponse": (ROOT / "src/types/index.ts", "EmergencyIntakeResponse"),
    "EmergencyEvidenceUploadResponse": (ROOT / "src/types/index.ts", "EmergencyEvidenceUploadResponse"),
    "ServiceHealth": (ROOT / "src/types/index.ts", "BackendServiceHealth"),
    "IncidentResponse": (ROOT / "src/types/index.ts", "BackendIncident"),
    "IncidentListResponse": (ROOT / "src/types/index.ts", "IncidentListResponse"),
    "KpiResponse": (ROOT / "src/types/index.ts", "KpiResponse"),
    "EndpointResponse": (ROOT / "src/types/index.ts", "BackendEndpoint"),
    "SettingsResponse": (ROOT / "src/types/index.ts", "SettingsResponse"),
    "EndpointDeleteResponse": (ROOT / "src/types/index.ts", "EndpointDeleteResponse"),
    "DbTableInfo": (ROOT / "src/types/index.ts", "DatabaseTableInfo"),
    "DbTableRowsResponse": (ROOT / "src/types/index.ts", "DatabaseRowsResponse"),
    "DbSchemaResponse": (ROOT / "src/types/index.ts", "DatabaseSchemaResponse"),
    "DbExportResponse": (ROOT / "src/types/index.ts", "DatabaseExportResponse"),
    "StreamEvent": (ROOT / "src/types/index.ts", "StreamEvent"),
}
RESPONSE_MODELS: tuple[type[BaseModel], ...] = (
    HealthResponse,
    ProbeResponse,
    ChaosInjectionResponse,
    RemediationResponse,
    EmergencyIntakeResponse,
    EmergencyEvidenceUploadResponse,
    ServiceHealth,
    IncidentResponse,
    IncidentListResponse,
    KpiResponse,
    EndpointResponse,
    SettingsResponse,
    EndpointDeleteResponse,
    DbTableInfo,
    DbTablesResponse,
    DbTableRowsResponse,
    DbSchemaResponse,
    DbExportResponse,
    StreamEvent,
)
SECRET_PATTERNS = (
    re.compile(r"\bBearer\s+\S+", re.I),
    re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+\b"),
    re.compile(r"\b(?:sk-[A-Za-z0-9_-]{12,}|AIza[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(?:password|passwd|pwd|token|api[_-]?key|secret)\s*[:=]\s*[^,\s;}]+", re.I),
)


def _ts_fields(path: Path, name: str) -> set[str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(
        rf"export\s+interface\s+{re.escape(name)}\s*\{{(.*?)^\}}",
        source,
        flags=re.S | re.M,
    )
    if not match:
        raise AssertionError(f"Could not find TypeScript interface {name} in {path}")
    return set(re.findall(r"^  ([A-Za-z_$][\w$]*)\??\s*:", match.group(1), flags=re.M))


def assert_contract_typescript() -> None:
    schemas_module = sys.modules["backend.schemas"]
    mismatches: list[str] = []
    for model in RESPONSE_MODELS:
        mapping = TYPE_SCRIPT_INTERFACES.get(model.__name__)
        if mapping is None:
            continue
        path, interface_name = mapping
        ts_fields = _ts_fields(path, interface_name)
        json_fields = set(model.model_json_schema(by_alias=True).get("properties", {}))
        if json_fields != ts_fields:
            mismatches.append(
                f"{model.__name__} ↔ {interface_name}: backend-only="
                f"{sorted(json_fields - ts_fields)}, frontend-only={sorted(ts_fields - json_fields)}"
            )
    if mismatches:
        raise AssertionError("Pydantic/TypeScript contract mismatch:\n" + "\n".join(mismatches))


def _resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = schema.get("$ref")
    if not reference:
        return schema
    current: Any = root
    for part in reference.removeprefix("#/").split("/"):
        current = current[part]
    return current


def _assert_json_shape(value: Any, schema: dict[str, Any], root: dict[str, Any], path: str) -> None:
    schema = _resolve_ref(schema, root)
    if "anyOf" in schema:
        if value is None and any(_resolve_ref(option, root).get("type") == "null" for option in schema["anyOf"]):
            return
        options = [option for option in schema["anyOf"] if _resolve_ref(option, root).get("type") != "null"]
        for option in options:
            try:
                _assert_json_shape(value, option, root, path)
                return
            except AssertionError:
                continue
        raise AssertionError(f"{path} does not match any allowed schema variant")
    expected_type = schema.get("type")
    if expected_type == "object" or "properties" in schema:
        if not isinstance(value, dict):
            raise AssertionError(f"{path} should be an object")
        properties = schema.get("properties", {})
        required = set(schema.get("required", ()))
        if not required.issubset(value):
            raise AssertionError(f"{path} is missing keys: {sorted(required - value.keys())}")
        if schema.get("additionalProperties") is not True:
            extras = set(value) - set(properties)
            if extras:
                raise AssertionError(f"{path} has unexpected keys: {sorted(extras)}")
        for key, child in properties.items():
            if key in value:
                _assert_json_shape(value[key], child, root, f"{path}.{key}")
        extra_schema = schema.get("additionalProperties")
        if isinstance(extra_schema, dict):
            for key in set(value) - set(properties):
                _assert_json_shape(value[key], extra_schema, root, f"{path}.{key}")
    elif expected_type == "array":
        if not isinstance(value, list):
            raise AssertionError(f"{path} should be an array")
        for index, item in enumerate(value):
            _assert_json_shape(item, schema.get("items", {}), root, f"{path}[{index}]")


def assert_response(response: httpx.Response, model: type[BaseModel], *, array: bool = False) -> Any:
    response.raise_for_status()
    payload = response.json()
    if array:
        if not isinstance(payload, list):
            raise AssertionError(f"{response.request.url} should return a JSON array")
        schema = model.model_json_schema(by_alias=True)
        for index, item in enumerate(payload):
            _assert_json_shape(item, schema, schema, f"response[{index}]")
            model.model_validate(item)
    else:
        schema = model.model_json_schema(by_alias=True)
        _assert_json_shape(payload, schema, schema, "response")
        model.model_validate(payload)
    return payload


def _check_no_secrets(logs: list[dict[str, Any]]) -> None:
    for log in logs:
        message = str(log.get("message", ""))
        for pattern in SECRET_PATTERNS:
            if pattern.search(message):
                raise AssertionError(f"Potential secret found in incident log {log.get('ts')}")


def run_down_check() -> str:
    try:
        httpx.get("http://127.0.0.1:0/health", timeout=0.3)
    except httpx.ConnectError:
        return "PASS: unavailable backend is surfaced as a connection failure"
    raise AssertionError("Port 0 unexpectedly accepted a connection")


def run_failure_checks(client: httpx.Client, base_url: str, headers: dict[str, str]) -> list[str]:
    results = [run_down_check()]

    wrong_key = client.get(f"{base_url}/api/settings", headers={"X-API-Key": "intentionally-wrong"})
    if wrong_key.status_code == 401:
        results.append("PASS: wrong API key returns 401 UNAUTHORIZED")
    elif wrong_key.status_code == 200 and not headers.get("X-API-Key"):
        results.append("SKIP: wrong-key enforcement requires AUTH_ENABLED=true and a configured API_KEY")
    else:
        raise AssertionError(f"Wrong-key check returned unexpected HTTP {wrong_key.status_code}")

    allowed_preflight = client.options(
        f"{base_url}/api/settings",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    denied_preflight = client.options(
        f"{base_url}/api/settings",
        headers={
            "Origin": "https://not-allowed.invalid",
            "Access-Control-Request-Method": "GET",
        },
    )
    if allowed_preflight.headers.get("access-control-allow-origin") == "http://localhost:3000" \
            and "access-control-allow-origin" not in denied_preflight.headers:
        results.append("PASS: allowed CORS origin is permitted; non-allowed origin receives no allow-origin header")
    else:
        raise AssertionError("CORS allowlist check failed")

    for _attempt in range(2):
        with client.stream(
            "GET",
            f"{base_url}/api/stream/events",
            headers=headers,
            timeout=3,
        ) as stream:
            if stream.status_code != 200 or "text/event-stream" not in stream.headers.get("content-type", ""):
                raise AssertionError("SSE endpoint did not establish an event-stream response")
    results.append("PASS: closing an SSE stream and reconnecting succeeds")
    return results


def run_integration(base_url: str, api_key: str | None, timeout: float) -> list[str]:
    headers = {"X-API-Key": api_key} if api_key else {}
    outcomes: list[str] = []
    endpoint_id: int | None = None
    old_settings: dict[str, Any] | None = None
    base_url = base_url.rstrip("/")

    with httpx.Client(timeout=10, follow_redirects=False) as client:
        health = client.get(f"{base_url}/health")
        assert_response(health, HealthResponse)
        outcomes.append("PASS: GET /health")
        assert_contract_typescript()
        outcomes.append("PASS: generated Pydantic JSON Schema field names match mapped TypeScript interfaces")

        suffix = uuid.uuid4().hex[:10]
        endpoint_payload = {
            "name": f"integration-{suffix}",
            "url": "http://127.0.0.1:5001/healthz",
            "serviceKey": f"integration-{suffix}",
            "port": 5001,
            "probeIntervalSeconds": 2,
            "enabled": True,
        }
        add_response = client.post(
            f"{base_url}/api/endpoints",
            headers=headers,
            json=endpoint_payload,
        )
        endpoint = assert_response(add_response, EndpointResponse)
        endpoint_id = endpoint["id"]
        outcomes.append("PASS: POST /api/endpoints")

        probe_response = client.get(
            f"{base_url}/api/probe",
            headers=headers,
            params={"url": endpoint_payload["url"]},
        )
        assert_response(probe_response, ProbeResponse)
        outcomes.append("PASS: GET /api/probe")

        kpis_before = assert_response(client.get(f"{base_url}/api/kpis", headers=headers), KpiResponse)
        old_settings = assert_response(client.get(f"{base_url}/api/settings", headers=headers), SettingsResponse)
        settings_response = client.put(
            f"{base_url}/api/settings",
            headers=headers,
            json={"zeroTouchEnabled": True},
        )
        assert_response(settings_response, SettingsResponse)
        outcomes.append("PASS: enabled zero-touch for the integration incident")

        try:
            baseline_ids = {
                incident["id"]
                for incident in assert_response(
                    client.get(f"{base_url}/api/incidents", headers=headers, params={"limit": 500}),
                    IncidentListResponse,
                )["incidents"]
            }
            chaos_response = client.post(
                f"{base_url}/api/chaos/inject",
                headers=headers,
                json={"service": "api", "port": 5002, "type": "CRASH"},
            )
            assert_response(chaos_response, ChaosInjectionResponse)
            outcomes.append("PASS: POST /api/chaos/inject CRASH api:5002")

            deadline = time.monotonic() + timeout
            verified_incident: dict[str, Any] | None = None
            while time.monotonic() < deadline:
                response = client.get(
                    f"{base_url}/api/incidents",
                    headers=headers,
                    params={"limit": 500, "service": "api"},
                )
                incident_list = assert_response(response, IncidentListResponse)
                for item in incident_list["incidents"]:
                    if item["id"] not in baseline_ids and item["status"] == "verified":
                        verified_incident = item
                        break
                if verified_incident:
                    break
                time.sleep(0.5)
            if verified_incident is None:
                current = client.get(f"{base_url}/api/incidents", headers=headers, params={"limit": 500, "service": "api"})
                current.raise_for_status()
                raise AssertionError(f"New API incident did not reach verified within {timeout:g}s: {current.json()}")

            assert_response(
                client.get(f"{base_url}/api/incidents/{verified_incident['id']}", headers=headers),
                IncidentResponse,
            )
            _check_no_secrets(verified_incident["logs"])
            if not verified_incident["autoHealed"]:
                raise AssertionError("Incident reached verified but autoHealed was false")
            stage_times = [
                verified_incident[field]
                for field in ("injectedAt", "detectedAt", "diagnosedAt", "fixedAt", "verifiedAt")
            ]
            if any(value is None for value in stage_times):
                raise AssertionError("Verified incident is missing one or more stage timestamps")
            parsed_times = [
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                for value in stage_times
            ]
            if parsed_times != sorted(parsed_times):
                raise AssertionError("Incident stage timestamps are not monotonic")
            outcomes.append("PASS: incident reached verified, autoHealed=true, logs are redacted")
            if any("LLM diagnosis fallback" in log["message"] for log in verified_incident["logs"]):
                outcomes.append("PASS: LLM missing-key/provider failure used the rule-based fallback while self-healing completed")
            else:
                outcomes.append("NOT PROVEN: this run did not observe LLM fallback; unset the selected provider key and restart backend to test missing-key mode")

            kpis_after = assert_response(client.get(f"{base_url}/api/kpis", headers=headers), KpiResponse)
            if kpis_after["totalIncidents"] <= kpis_before["totalIncidents"]:
                raise AssertionError("KPI totalIncidents did not increase after the integration incident")
            outcomes.append("PASS: KPI totals changed after incident timestamps were recorded")
        finally:
            if old_settings is not None:
                client.put(f"{base_url}/api/settings", headers=headers, json=old_settings)
            if endpoint_id is not None:
                delete_response = client.delete(f"{base_url}/api/endpoints/{endpoint_id}", headers=headers)
                if delete_response.status_code == 200:
                    assert_response(delete_response, EndpointDeleteResponse)

        outcomes.extend(run_failure_checks(client, base_url, headers))
    return outcomes


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:5000")
    parser.add_argument("--api-key", default=None, help="API key for AUTH_ENABLED deployments (not printed)")
    parser.add_argument("--timeout", type=float, default=45, help="Seconds to wait for the incident to verify")
    parser.add_argument("--failure-modes-only", action="store_true")
    parser.add_argument("--contracts-only", action="store_true")
    args = parser.parse_args()
    headers = {"X-API-Key": args.api_key} if args.api_key else {}
    try:
        if args.contracts_only:
            assert_contract_typescript()
            outcomes = ["PASS: generated Pydantic JSON Schema field names match mapped TypeScript interfaces"]
        elif args.failure_modes_only:
            with httpx.Client(timeout=10, follow_redirects=False) as client:
                outcomes = run_failure_checks(client, args.base_url.rstrip("/"), headers)
        else:
            outcomes = run_integration(args.base_url, args.api_key, args.timeout)
    except (httpx.HTTPError, AssertionError, KeyError, ValueError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for outcome in outcomes:
        print(outcome)
    print(f"Integration result: {len([item for item in outcomes if item.startswith('PASS')])} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
