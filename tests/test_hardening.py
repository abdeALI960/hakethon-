import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from pydantic import SecretStr

from backend.config import settings
from backend.database import get_db
from backend.main import create_app
from backend.middleware import _rate_limiter
from backend.models import Base, Endpoint, Incident, IncidentLog, utc_now
from backend.services.events import publish_log_event, subscribe_events


class HardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "hardening.db"
        self.engine = create_engine(
            f"sqlite:///{self.database_path}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(self.engine)
        self.previous_database_url = settings.database_url
        settings.database_url = f"sqlite:///{self.database_path}"
        self.app = create_app()
        self.app.dependency_overrides[get_db] = self._override_get_db
        self.create_all_patcher = patch("backend.main.create_all")
        self.monitor_patcher = patch("backend.main.settings.monitor_enabled", False)
        self.create_all_patcher.start()
        self.monitor_patcher.start()
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()
        _rate_limiter._hits.clear()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.monitor_patcher.stop()
        self.create_all_patcher.stop()
        settings.database_url = self.previous_database_url
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _override_get_db(self):
        with Session(self.engine) as db:
            yield db

    def test_api_key_auth_protects_api_but_not_health(self) -> None:
        with (
            patch.object(settings, "auth_enabled", True),
            patch.object(settings, "api_key", SecretStr("do-not-log-this-key")),
        ):
            public_health = self.client.get("/health")
            missing_key = self.client.get("/api/settings")
            correct_key = self.client.get(
                "/api/settings",
                headers={"X-API-Key": "do-not-log-this-key"},
            )
        self.assertEqual(public_health.status_code, 200)
        self.assertEqual(missing_key.status_code, 401)
        self.assertEqual(missing_key.json()["error"]["code"], "UNAUTHORIZED")
        self.assertEqual(correct_key.status_code, 200)

    def test_cors_preflight_is_not_blocked_by_api_key_auth(self) -> None:
        with patch.object(settings, "auth_enabled", True):
            response = self.client.options(
                "/api/analyze",
                headers={
                    "Origin": "http://localhost:3000",
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,x-api-key",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://localhost:3000",
        )

    def test_rate_limit_returns_standard_error_and_retry_after(self) -> None:
        for _ in range(10):
            response = self.client.post("/api/analyze", json={"logs": "not-a-list"})
            self.assertEqual(response.status_code, 422)
        limited = self.client.post("/api/analyze", json={})
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(limited.json()["error"]["code"], "RATE_LIMITED")
        self.assertGreaterEqual(int(limited.headers["retry-after"]), 1)

    def test_request_body_cap_and_json_depth_are_enforced(self) -> None:
        too_large = self.client.post(
            "/api/analyze",
            content=b"x" * (6 * 1024 * 1024 + 1),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(too_large.json()["error"]["code"], "REQUEST_TOO_LARGE")

        nested: object = "deep"
        for _ in range(25):
            nested = {"value": nested}
        too_deep = self.client.post(
            "/api/analyze",
            content=json.dumps({"metrics": nested}).encode(),
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(too_deep.status_code, 422)
        self.assertEqual(too_deep.json()["error"]["code"], "VALIDATION_ERROR")

    def test_security_headers_and_request_id_are_added_even_to_errors(self) -> None:
        response = self.client.get(
            "/api/unknown",
            headers={"X-Request-ID": "hardening-test-1"},
        )
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["referrer-policy"], "no-referrer")
        self.assertEqual(response.headers["x-request-id"], "hardening-test-1")

    def test_production_disables_docs_and_openapi(self) -> None:
        with patch.object(settings, "env", "production"):
            app = create_app()
        self.assertIsNone(app.docs_url)
        self.assertIsNone(app.redoc_url)
        self.assertIsNone(app.openapi_url)

    def test_endpoint_registry_is_capped_at_fifty(self) -> None:
        with Session(self.engine) as db:
            db.add_all(
                [
                    Endpoint(
                        name=f"custom-{index}",
                        url=f"https://example{index}.test",
                        probe_interval_seconds=2,
                        enabled=True,
                        is_demo_target=False,
                    )
                    for index in range(50)
                ]
            )
            db.commit()
        with patch(
            "backend.routers.endpoints.validate_target_url",
            side_effect=AssertionError("capacity must be checked first"),
        ):
            response = self.client.post(
                "/api/endpoints",
                json={
                    "name": "fifty-first",
                    "url": "https://example.test",
                    "probeIntervalSeconds": 2.0,
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["error"]["code"], "ENDPOINT_LIMIT_REACHED")

    def test_secrets_in_incident_log_never_appear_in_api_responses(self) -> None:
        secret_log = (
            "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature password=hunter2"
        )
        with Session(self.engine) as db:
            incident = Incident(
                id="INC-LOG",
                service="api",
                port=5002,
                anomaly_type="CRASH",
                severity="CRIT",
                status="verified",
                auto_healed=False,
                created_at=utc_now(),
            )
            db.add(incident)
            db.flush()
            db.add(IncidentLog(incident_id=incident.id, level="INFO", message=secret_log))
            db.commit()

        responses = [
            self.client.get("/api/incidents/INC-LOG"),
            self.client.get("/api/incidents/export.md"),
            self.client.get("/api/db/tables/incident_logs"),
            self.client.get("/api/db/export"),
        ]
        for response in responses:
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", response.text)
            self.assertNotIn("eyJzdWIiOiIxMjM0NTY3ODkwIn0", response.text)
            self.assertNotIn("hunter2", response.text)

        async def get_event():
            events = subscribe_events()
            next_event = asyncio.create_task(events.__anext__())
            await asyncio.sleep(0)
            publish_log_event("INC-LOG", utc_now(), "INFO", secret_log)
            event = await next_event
            await events.aclose()
            return event

        event_text = json.dumps(asyncio.run(get_event()))
        self.assertNotIn("eyJhbGciOiJIUzI1NiJ9", event_text)
        self.assertNotIn("hunter2", event_text)

    def test_startup_self_check_logs_only_key_presence(self) -> None:
        from backend.middleware import startup_self_check

        with (
            patch.object(settings, "openai_api_key", SecretStr("provider-secret")),
            patch.object(settings, "anthropic_api_key", None),
            patch.object(settings, "gemini_api_key", None),
            self.assertLogs("opspilot.http", level="INFO") as captured,
        ):
            startup_self_check()
        fields = captured.records[-1].structured_fields
        self.assertTrue(fields["llm_provider_keys"]["openai"])
        rendered = json.dumps(fields)
        self.assertNotIn("provider-secret", rendered)

    def test_startup_warns_for_unauthenticated_non_local_chaos_bind(self) -> None:
        from backend.middleware import startup_self_check

        with (
            patch.object(settings, "chaos_enabled", True),
            patch.object(settings, "auth_enabled", False),
            patch("backend.middleware.sys.argv", ["uvicorn", "backend.main:app", "--host", "0.0.0.0"]),
            self.assertLogs("opspilot.http", level="WARNING") as captured,
        ):
            startup_self_check()
        self.assertTrue(any("unsafe_chaos_bind" in record.getMessage() for record in captured.records))


if __name__ == "__main__":
    unittest.main()
