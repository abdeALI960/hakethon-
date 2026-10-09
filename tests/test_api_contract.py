import asyncio
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.errors import AppError
from backend.main import create_app
from backend.models import Base, Endpoint
from backend.schemas import (
    ChaosInjectionRequest,
    EmergencyIntakeRequest,
    EndpointCreateRequest,
    RemediationRequest,
)
from backend.services.url_security import validate_target_url


class FrontendEnumContractTests(unittest.TestCase):
    def test_frontend_chaos_and_remediation_literals_are_accepted(self) -> None:
        chaos_values = (
            "CRASH",
            "CPU_SPIKE",
            "HIGH_LATENCY",
            "OOM_KILL",
        )
        for failure_type in chaos_values:
            payload = ChaosInjectionRequest.model_validate(
                {"service": "api", "port": 5002, "type": failure_type}
            )
            self.assertEqual(payload.type.value, failure_type)

        remediation_literals = (
            "restart",
            "python fixer.py restart api",
            'kill -SIGUSR1 $(pgrep -f "worker/spinloop")',
            "curl -X POST http://127.0.0.1:5001/admin/reset-delay",
        )
        for action in remediation_literals:
            payload = RemediationRequest.model_validate({"service": "api", "action": action})
            self.assertEqual(payload.action.value, action)

    def test_frontend_triage_and_probe_interval_literals_are_accepted(self) -> None:
        for priority in ("RED", "YELLOW", "GREEN"):
            intake = EmergencyIntakeRequest.model_validate(
                {
                    "incidentType": "Network interruption",
                    "location": "ICU Rack 04",
                    "priority": priority,
                    "reportedBy": "Lead SRE",
                    "description": "Packet loss exceeded 15%",
                }
            )
            self.assertEqual(intake.priority, priority)
        for interval in ("1s", "2s", "5s", 1.0, 2.0, 5.0):
            payload = EndpointCreateRequest.model_validate(
                {
                    "name": "external",
                    "url": "https://example.com",
                    "probeIntervalSeconds": interval,
                }
            )
            self.assertIn(payload.probe_interval_seconds, ("1s", "2s", "5s", 1, 2, 5))

    def test_all_requested_routes_publish_response_models(self) -> None:
        app = create_app()
        expected = {
            ("GET", "/api/probe"),
            ("POST", "/api/chaos/inject"),
            ("POST", "/api/remediate"),
            ("POST", "/api/emergency/intake"),
            ("POST", "/api/analyze"),
            ("GET", "/api/services/health"),
            ("GET", "/api/incidents"),
            ("GET", "/api/incidents/{incident_id}"),
            ("GET", "/api/kpis"),
            ("GET", "/api/endpoints"),
            ("POST", "/api/endpoints"),
            ("PATCH", "/api/endpoints/{endpoint_id}"),
            ("DELETE", "/api/endpoints/{endpoint_id}"),
            ("GET", "/api/settings"),
            ("PUT", "/api/settings"),
            ("GET", "/api/stream/events"),
        }
        routes = {
            (method, route.path): route
            for route in app.routes
            for method in getattr(route, "methods", set())
        }
        self.assertTrue(expected.issubset(routes.keys()))
        for key in expected:
            self.assertIsNotNone(routes[key].response_model, key)


class UrlSecurityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    def test_private_resolution_is_blocked_for_unregistered_host(self) -> None:
        with (
            patch(
                "backend.services.url_security.socket.getaddrinfo",
                return_value=[
                    (2, 1, 6, "", ("192.168.1.10", 443)),
                ],
            ),
            self.assertRaises(AppError) as raised,
        ):
            asyncio.run(validate_target_url(self.db, "https://service.example"))
        self.assertEqual(raised.exception.code, "SSRF_BLOCKED")

    def test_registered_demo_target_is_allowed_but_credentials_and_secrets_are_not(self) -> None:
        self.db.add(
            Endpoint(
                name="api",
                url="http://127.0.0.1:5002",
                service_key="api",
                port=5002,
                enabled=True,
                is_demo_target=True,
            )
        )
        self.db.commit()
        asyncio.run(validate_target_url(self.db, "http://127.0.0.1:5002"))
        with self.assertRaises(AppError):
            asyncio.run(validate_target_url(self.db, "http://user:pass@127.0.0.1:5002"))
        with self.assertRaises(AppError):
            asyncio.run(validate_target_url(self.db, "http://user:pass@127.0.0.1:5002"))
        with self.assertRaises(AppError):
            asyncio.run(validate_target_url(self.db, "https://example.com/?api_key=secret"))

    def test_webhook_requires_https_and_private_dns_is_rejected(self) -> None:
        with self.assertRaises(AppError):
            asyncio.run(validate_target_url(self.db, "http://example.com", https_only=True))
        with (
            patch(
                "backend.services.url_security.socket.getaddrinfo",
                return_value=[
                    (2, 1, 6, "", ("10.0.0.2", 443)),
                ],
            ),
            self.assertRaises(AppError) as raised,
        ):
            asyncio.run(
                validate_target_url(
                    self.db,
                    "https://webhook.example",
                    https_only=True,
                    allow_registered=False,
                )
            )
        self.assertEqual(raised.exception.code, "SSRF_BLOCKED")


class ApiErrorContractTests(unittest.TestCase):
    def test_health_and_validation_error_include_contract_fields(self) -> None:
        app = create_app()
        with (
            patch("backend.main.create_all"),
            patch("backend.main.settings.monitor_enabled", False),
            TestClient(app) as client,
        ):
            health = client.get("/health", headers={"X-Request-ID": "test-request-1"})
            self.assertEqual(
                health.json(),
                {"status": "ok", "service": "OpsPilot"},
            )
            self.assertEqual(health.headers["X-Request-ID"], "test-request-1")

            response = client.post("/api/chaos/inject", json={})
            body = response.json()
            self.assertEqual(response.status_code, 422)
            self.assertEqual(body["error"]["code"], "VALIDATION_ERROR")
            self.assertEqual(body["error"]["details"][0]["field"], "service")
            self.assertTrue(response.headers["X-Request-ID"])


if __name__ == "__main__":
    unittest.main()
