import asyncio
import re
import io
import json
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

from fastapi.routing import APIRoute
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import create_engine

from backend.config import settings
from backend.models import (
    Base,
    EmergencyCase,
    Endpoint,
    Incident,
    Remediation,
    RuntimeSettings,
)
from backend.services.executor import ExecutionResult
from backend.services.probe import Probe


def _keys(body: dict[str, Any]) -> set[str]:
    return set(body)


def test_readme_golden_response_examples(api, monkeypatch) -> None:
    client = api.client
    fixed_time = datetime(2026, 10, 9, 14, 35, 2, tzinfo=timezone.utc)

    with api.db_factory() as db:
        db.add_all(
            [
                Endpoint(
                    name=service,
                    url=f"http://127.0.0.1:{port}",
                    service_key=service,
                    port=port,
                    enabled=True,
                    is_demo_target=True,
                )
                for service, port in (("web", 5001), ("api", 5002), ("worker", 5003))
            ]
        )
        db.add(RuntimeSettings(id=1, zero_touch_enabled=False))
        db.commit()

    async def fake_validate(*_args, **_kwargs):
        return None

    async def fake_probe(*_args, **_kwargs):
        return Probe(200, 18, True, fixed_time, ssl_cert_days=242)

    monkeypatch.setattr("backend.routers.probe.validate_target_url", fake_validate)
    monkeypatch.setattr("backend.routers.probe.probe_endpoint", fake_probe)
    response = client.get("/api/probe", params={"url": "http://127.0.0.1:5002"})
    assert response.status_code == 200
    assert response.json() == {
        "httpStatus": 200,
        "pingLatencyMs": 18.0,
        "sslCertDays": 242,
        "lastCheckedUtc": "2026-10-09T14:35:02Z",
    }

    monkeypatch.setattr(settings, "chaos_enabled", True)
    monkeypatch.setattr(
        "backend.routers.chaos.execute_chaos",
        AsyncMock(return_value=ExecutionResult(True, None, "ok", 0.01)),
    )
    response = client.post(
        "/api/chaos/inject",
        json={"service": "api", "port": 5002, "type": "CRASH"},
    )
    assert response.status_code == 201
    assert response.json() == {
        "status": "injected",
        "command": "python inject.py crash --target api:5002",
        "targetPid": None,
    }

    with api.db_factory() as db:
        incident = Incident(
            id="INC-APPROVAL",
            service="web",
            port=5001,
            anomaly_type="LATENCY",
            severity="WARN",
            status="awaiting_approval",
            auto_healed=False,
        )
        db.add(incident)
        db.commit()

    async def fake_remediate(db, incident, _endpoint, action):
        incident.status = "verified"
        db.add(
            Remediation(
                incident_id=incident.id,
                action=action.value,
                executed_by="human",
                status="verified",
                new_pid=48291,
                probe_verified=True,
                fix_duration_sec=1.4,
            )
        )
        db.commit()
        return incident

    monkeypatch.setattr("backend.routers.remediate.remediate_incident", fake_remediate)
    response = client.post(
        "/api/remediate",
        json={"service": "web", "action": "clear_latency"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "recovered",
        "newPid": 48291,
        "probeVerified": True,
        "fixDurationSec": 1.4,
    }

    monkeypatch.setattr(
        "backend.routers.emergency.triage_emergency",
        AsyncMock(
            return_value={
                "summary": "Critical Priority Level 1: Immediate failover triggered.",
                "llmStatus": "ok",
            }
        ),
    )
    response = client.post(
        "/api/emergency/intake",
        json={
            "incidentType": "Cardiac Telemetry Gateway Dropout",
            "location": "ICU Rack 04",
            "priority": "RED",
            "reportedBy": "Lead SRE",
            "description": "Packet loss exceeded 15%",
        },
    )
    assert response.status_code == 201
    emergency = response.json()
    assert _keys(emergency) == {"caseId", "status", "aiTriageSummary", "safetyNotice"}
    assert re.fullmatch(r"EMG-\d{4}", emergency["caseId"])
    assert emergency["status"] == "Dispatched"
    assert emergency["aiTriageSummary"] == (
        "Critical Priority Level 1: Immediate failover triggered."
    )
    assert emergency["safetyNotice"] == (
        "AI output is decision support only and does not replace professional human evaluation."
    )


def test_all_route_response_schemas_publish_camel_case_fields(api) -> None:
    routes = [
        route for route in api.app.routes
        if isinstance(route, APIRoute) and route.path.startswith("/api/")
    ]
    assert routes
    json_routes = [route for route in routes if route.response_model is not None]
    binary_routes = [route for route in routes if route.response_model is None]
    assert len(json_routes) == len(routes) - 1
    assert [(route.path, route.methods) for route in binary_routes] == [
        ("/api/emergency/{case_id}/evidence", {"GET"})
    ]

    def check_schema(schema: dict[str, Any]) -> None:
        for field in schema.get("properties", {}):
            assert "_" not in field, (schema, field)
        for nested in schema.get("$defs", {}).values():
            check_schema(nested)

    for route in json_routes:
        model = route.response_model
        if hasattr(model, "model_json_schema"):
            check_schema(model.model_json_schema(by_alias=True))
        elif isinstance(model, list) and model and hasattr(model[0], "model_json_schema"):
            check_schema(model[0].model_json_schema(by_alias=True))


def test_frontend_route_responses_have_exact_field_sets(
    api,
    monkeypatch,
    temp_sqlite,
    tmp_path,
) -> None:
    client = api.client
    with api.db_factory() as db:
        db.add_all(
            [
                Endpoint(
                    name=service,
                    url=f"http://127.0.0.1:{port}",
                    service_key=service,
                    port=port,
                    enabled=True,
                    is_demo_target=True,
                )
                for service, port in (("web", 5001), ("api", 5002), ("worker", 5003))
            ]
        )
        db.commit()
    monkeypatch.setattr(
        "backend.routers.emergency.triage_emergency",
        AsyncMock(return_value={"summary": "Safe summary.", "llmStatus": "ok"}),
    )
    monkeypatch.setattr(
        "backend.routers.analyze.analyze_telemetry",
        AsyncMock(
            return_value={
                "summary": "Connection failure",
                "rootCause": "Connection refused",
                "confidence": 0.9,
                "severity": "CRIT",
                "recommendedAction": "restart",
                "rationale": "The service is unavailable.",
                "evidence": ["health probe failed"],
                "llmStatus": "ok",
                "latencyMs": 3.0,
            }
        ),
    )

    health = client.get("/health")
    assert health.json() == {"status": "ok", "service": "OpsPilot"}

    body = {
        "incidentType": "Network interruption",
        "location": "Rack 04",
        "priority": "YELLOW",
        "reportedBy": "Operator",
        "description": "Packet loss",
    }
    emergency = client.post("/api/emergency/intake", json=body)
    assert emergency.status_code == 201
    assert _keys(emergency.json()) == {
        "caseId",
        "status",
        "aiTriageSummary",
        "safetyNotice",
    }

    analyze_request = {"metrics": {"service": "api"}, "logs": ["connection refused"]}
    analyze = client.post("/api/analyze", json=analyze_request)
    legacy_analyze = client.post("/analyze", json=analyze_request)
    expected_analysis_keys = {
        "summary",
        "rootCause",
        "confidence",
        "severity",
        "recommendedAction",
        "rationale",
        "evidence",
        "llmStatus",
        "latencyMs",
        "incidentId",
    }
    assert analyze.status_code == legacy_analyze.status_code == 200
    assert _keys(analyze.json()) == expected_analysis_keys
    assert _keys(legacy_analyze.json()) == expected_analysis_keys

    incident_list = client.get("/api/incidents").json()
    assert _keys(incident_list) == {
        "incidents",
        "total",
        "limit",
        "offset",
    }
    incident_id = analyze.json()["incidentId"]
    assert _keys(incident_list["incidents"][0]) == {
        "id",
        "service",
        "port",
        "anomalyType",
        "severity",
        "autoHealed",
        "status",
        "injectedAt",
        "detectedAt",
        "diagnosedAt",
        "fixedAt",
        "verifiedAt",
        "detectionDurationSec",
        "fixDurationSec",
        "aiRationale",
        "logs",
    }
    detail = client.get(f"/api/incidents/{incident_id}")
    assert detail.status_code == 200
    assert _keys(detail.json()) == _keys(incident_list["incidents"][0])

    assert _keys(client.get("/api/kpis").json()) == {
        "totalIncidents",
        "autoHealedRatePercent",
        "humanEscalations",
        "mttdSeconds",
        "mttrSeconds",
    }
    service_health = client.get("/api/services/health")
    assert service_health.status_code == 200
    assert _keys(service_health.json()[0]) == {
        "service",
        "port",
        "status",
        "latencyMs",
        "lastCheckedUtc",
    }

    settings_fields = {
        "llmProvider",
        "p99LatencySlaMs",
        "webhookUrl",
        "zeroTouchEnabled",
        "operatorName",
    }
    assert _keys(client.get("/api/settings").json()) == settings_fields
    updated_settings = client.put(
        "/api/settings",
        json={"operatorName": "Test Operator", "zeroTouchEnabled": True},
    )
    assert updated_settings.status_code == 200
    assert _keys(updated_settings.json()) == settings_fields

    endpoints = client.get("/api/endpoints")
    assert endpoints.status_code == 200
    assert isinstance(endpoints.json(), list)
    endpoint_fields = {
        "id",
        "name",
        "url",
        "serviceKey",
        "port",
        "probeIntervalSeconds",
        "enabled",
        "isDemoTarget",
        "createdAt",
    }
    assert _keys(endpoints.json()[0]) == endpoint_fields

    async def fake_validate(*_args, **_kwargs):
        return None

    monkeypatch.setattr("backend.routers.endpoints.validate_target_url", fake_validate)
    created_endpoint = client.post(
        "/api/endpoints",
        json={
            "name": "contract-target",
            "url": "https://contract.example",
            "serviceKey": "contract-target",
            "probeIntervalSeconds": 2.0,
        },
    )
    assert created_endpoint.status_code == 201
    assert _keys(created_endpoint.json()) == endpoint_fields
    endpoint_id = created_endpoint.json()["id"]
    patched_endpoint = client.patch(
        f"/api/endpoints/{endpoint_id}",
        json={"enabled": False},
    )
    assert patched_endpoint.status_code == 200
    assert _keys(patched_endpoint.json()) == endpoint_fields
    deleted_endpoint = client.delete(f"/api/endpoints/{endpoint_id}")
    assert deleted_endpoint.status_code == 200
    assert deleted_endpoint.json() == {"deleted": True}

    file_engine = create_engine(f"sqlite:///{temp_sqlite}")
    Base.metadata.create_all(file_engine)
    file_engine.dispose()
    tables = client.get("/api/db/tables")
    assert tables.status_code == 200
    assert _keys(tables.json()) == {"tables"}
    assert _keys(tables.json()["tables"][0]) == {"name", "rowCount"}
    rows = client.get("/api/db/tables/incidents")
    assert rows.status_code == 200
    assert _keys(rows.json()) == {"table", "rows", "total", "limit", "offset", "q"}
    schema = client.get("/api/db/schema")
    assert schema.status_code == 200
    assert _keys(schema.json()) == {"tables"}
    assert _keys(schema.json()["tables"][0]) == {"name", "createSql"}
    exported = client.get("/api/db/export")
    assert exported.status_code == 200
    assert _keys(exported.json()) == {"tables", "rowCount", "rowCap", "truncated"}

    upload_root = tmp_path / "api-contract-uploads"
    monkeypatch.setattr("backend.routers.emergency.UPLOAD_ROOT", upload_root)
    monkeypatch.setattr(settings, "api_key", SecretStr("contract-key"))
    with api.db_factory() as db:
        db.add(
            EmergencyCase(
                case_id="EMG-5555",
                incident_type="Network",
                location="Rack",
                priority="GREEN",
                reported_by="operator",
                description="Telemetry issue",
                status="Dispatched",
                ai_triage_summary="Monitor.",
                llm_status="failed",
            )
        )
        db.commit()
    image_bytes = io.BytesIO()
    Image.new("RGB", (2, 2), color="white").save(image_bytes, format="PNG")
    upload = client.post(
        "/api/emergency/EMG-5555/evidence",
        files={"upload": ("client-name.png", image_bytes.getvalue(), "image/png")},
        headers={"X-API-Key": "contract-key"},
    )
    assert upload.status_code == 201
    assert upload.json() == {
        "caseId": "EMG-5555",
        "status": "uploaded",
        "contentType": "image/png",
    }

    from backend.routers.stream import _event_stream
    from backend.services.events import publish_event

    async def next_sse_event() -> dict[str, Any]:
        stream = _event_stream()
        pending = asyncio.create_task(stream.__anext__())
        await asyncio.sleep(0)
        publish_event("INC-SSE", "detected", "detected", endpoint_id=42)
        raw = await asyncio.wait_for(pending, timeout=1)
        await stream.aclose()
        return json.loads(raw.removeprefix("data: "))

    event = asyncio.run(next_sse_event())
    assert _keys(event) == {"type", "incidentId", "endpointId", "timestamp", "payload"}
