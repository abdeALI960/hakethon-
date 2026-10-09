import asyncio
from datetime import datetime, timedelta, timezone
import sqlite3
from unittest.mock import patch

import pytest
from pydantic import SecretStr
from sqlalchemy import create_engine

from backend.config import settings
from backend.errors import AppError
from backend.models import Base, EmergencyCase, Incident, utc_now
from backend.services.executor import DemoService, DemoTarget, execute_chaos, ChaosAction
from backend.services.url_security import validate_target_url


def test_ssrf_blocks_private_and_metadata_addresses(api, monkeypatch: pytest.MonkeyPatch) -> None:
    def resolve(*_args, **_kwargs):
        return [(2, 1, 6, "", ("169.254.169.254", 443))]

    monkeypatch.setattr("backend.services.url_security.socket.getaddrinfo", resolve)
    with api.db_factory() as db:
        with pytest.raises(AppError) as error:
            asyncio.run(validate_target_url(db, "https://metadata.example"))
    assert error.value.code == "SSRF_BLOCKED"


def test_executor_rejects_unallowlisted_target_before_process_start(api) -> None:
    with patch("backend.services.executor.subprocess.run") as run:
        with pytest.raises(ValueError):
            DemoTarget("api; rm -rf /", 5002)  # type: ignore[arg-type]
        with pytest.raises(ValueError):
            DemoTarget(DemoService.API, 22)
        with pytest.raises(AppError) as error:
            asyncio.run(
                execute_chaos(
                    ChaosAction.CRASH,
                    DemoTarget(DemoService.API, 5002),
                )
            )
        assert error.value.code == "CHAOS_DISABLED"
        run.assert_not_called()


def test_db_inspector_rejects_identifier_and_parameter_injection(
    api,
    temp_sqlite,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    file_engine = create_engine(f"sqlite:///{temp_sqlite}")
    Base.metadata.create_all(file_engine)
    with file_engine.begin() as connection:
        connection.execute(
            Incident.__table__.insert().values(
                id="INC-DB-1",
                service="api",
                port=5002,
                anomaly_type="CRASH",
                severity="CRIT",
                status="verified",
                auto_healed=False,
                created_at=utc_now(),
            )
        )

    response = api.client.get("/api/db/tables/incidents%3BDELETE%20FROM%20incidents")
    assert response.status_code == 404
    query_attack = api.client.get(
        "/api/db/tables/incidents",
        params={"q": "' OR 1=1 --"},
    )
    assert query_attack.status_code == 200
    assert query_attack.json()["rows"] == []
    assert query_attack.json()["total"] == 0
    with sqlite3.connect(temp_sqlite) as connection:
        assert connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 1
    file_engine.dispose()


@pytest.mark.parametrize(
    ("filename", "content", "expected_code"),
    [
        ("oversized.png", b"x" * (5 * 1024 * 1024 + 1), "EVIDENCE_TOO_LARGE"),
        ("spoofed.png", b"not an image", "INVALID_EVIDENCE_IMAGE"),
    ],
)
def test_evidence_upload_rejects_oversize_and_mime_spoof(
    api,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
    filename: str,
    content: bytes,
    expected_code: str,
) -> None:
    monkeypatch.setattr(settings, "api_key", SecretStr("test-evidence-key"))
    monkeypatch.setattr("backend.routers.emergency.UPLOAD_ROOT", tmp_path / "uploads")
    with api.db_factory() as db:
        db.add(
            EmergencyCase(
                case_id="EMG-1234",
                incident_type="Network",
                location="Rack",
                priority="RED",
                reported_by="operator",
                description="Service outage",
                status="Dispatched",
                ai_triage_summary="Escalate",
                llm_status="failed",
            )
        )
        db.commit()

    response = api.client.post(
        "/api/emergency/EMG-1234/evidence",
        files={"upload": (filename, content, "image/png")},
        headers={"X-API-Key": "test-evidence-key"},
    )
    assert response.status_code == (413 if expected_code == "EVIDENCE_TOO_LARGE" else 415)
    assert response.json()["error"]["code"] == expected_code
    assert not (tmp_path / "uploads").exists()


def test_rate_limit_and_authentication_are_enforced(api, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "api_key", SecretStr("api-test-key"))
    unauthorized = api.client.get("/api/settings")
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "UNAUTHORIZED"
    assert api.client.get("/health").status_code == 200
    assert api.client.get(
        "/api/settings",
        headers={"X-API-Key": "api-test-key"},
    ).status_code == 200

    monkeypatch.setattr(settings, "auth_enabled", False)
    responses = [
        api.client.post("/api/analyze", json={"logs": "must-be-a-list"})
        for _ in range(10)
    ]
    assert all(response.status_code == 422 for response in responses)
    limited = api.client.post("/api/analyze", json={"logs": "must-be-a-list"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"
    assert int(limited.headers["Retry-After"]) >= 1


def test_empty_kpis_are_zeroes(api) -> None:
    response = api.client.get("/api/kpis")
    assert response.status_code == 200
    assert response.json() == {
        "totalIncidents": 0,
        "autoHealedRatePercent": 0.0,
        "humanEscalations": 0,
        "mttdSeconds": {"avg": 0.0, "stdDev": 0.0},
        "mttrSeconds": {"avg": 0.0},
    }


def test_kpis_derive_durations_from_persisted_timestamps(api) -> None:
    base = datetime(2026, 10, 10, tzinfo=timezone.utc)
    incidents = [
        Incident(
            id="INC-KPI-1",
            service="api",
            anomaly_type="CRASH",
            severity="CRIT",
            status="verified",
            auto_healed=True,
            injected_at=base,
            detected_at=base + timedelta(seconds=2),
            verified_at=base + timedelta(seconds=7),
            created_at=base,
        ),
        Incident(
            id="INC-KPI-2",
            service="web",
            anomaly_type="LATENCY",
            severity="WARN",
            status="awaiting_approval",
            auto_healed=False,
            injected_at=base,
            detected_at=base + timedelta(seconds=4),
            verified_at=base + timedelta(seconds=11),
            created_at=base,
        ),
    ]
    with api.db_factory() as db:
        db.add_all(incidents)
        db.commit()

    result = api.client.get("/api/kpis").json()
    assert result == {
        "totalIncidents": 2,
        "autoHealedRatePercent": 50.0,
        "humanEscalations": 1,
        "mttdSeconds": {"avg": 3.0, "stdDev": 1.0},
        "mttrSeconds": {"avg": 6.0},
    }
