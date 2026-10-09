import sqlite3
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import get_db
from backend.main import create_app
from backend.models import (
    Analysis,
    Base,
    EmergencyCase,
    Incident,
    IncidentLog,
    RuntimeSettings,
)
from backend.routers.db_inspector import _readonly_connection
from backend.models import utc_now


class DbInspectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "inspector.db"
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        Base.metadata.create_all(self.engine)
        with Session(self.engine) as db:
            incident = Incident(
                id="INC-101",
                service="api",
                port=5002,
                anomaly_type="CRASH",
                severity="CRIT",
                status="verified",
                auto_healed=True,
                injected_at=utc_now(),
                detected_at=utc_now(),
                verified_at=utc_now(),
                created_at=utc_now(),
            )
            db.add(incident)
            db.flush()
            db.add(
                IncidentLog(
                    incident_id=incident.id,
                    level="INFO",
                    message="Service recovered",
                )
            )
            db.add(
                Analysis(
                    incident_id=incident.id,
                    provider="openai",
                    model="test",
                    llm_status="ok",
                    root_cause="Process crash",
                    confidence=0.9,
                    recommended_action="restart",
                    rationale="Process was not responding.",
                    raw_report={"rationale": "Process was not responding."},
                    latency_ms=4.2,
                )
            )
            db.add(
                EmergencyCase(
                    case_id="EMG-1111",
                    incident_type="Network loss",
                    location="Rack 01",
                    priority="RED",
                    reported_by="On-call",
                    description="Network route failed",
                    status="Dispatched",
                    ai_triage_summary="Escalate.",
                    llm_status="failed",
                    evidence_path="uploads/private-file.png",
                )
            )
            db.add(
                # Ensure URL query strings are removed from inspector output.
                RuntimeSettings(
                    id=1,
                    llm_provider="openai",
                    p99_latency_sla_ms=1000,
                    webhook_url="https://hooks.example/notify?token=secret-value",
                    zero_touch_enabled=False,
                    operator_name="test",
                )
            )
            db.commit()
        with self.engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE private_table (secret TEXT)")

        self.old_database_url = settings.database_url
        settings.database_url = f"sqlite:///{self.db_path}"
        self.app = create_app()
        self.app.dependency_overrides[get_db] = self._override_get_db
        self.create_all_patcher = patch("backend.main.create_all")
        self.monitor_patcher = patch("backend.main.settings.monitor_enabled", False)
        self.create_all_patcher.start()
        self.monitor_patcher.start()
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()

    def _override_get_db(self):
        with Session(self.engine) as db:
            yield db

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.monitor_patcher.stop()
        self.create_all_patcher.stop()
        settings.database_url = self.old_database_url
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_tables_endpoint_excludes_secrets_and_non_allowlisted_tables(self) -> None:
        response = self.client.get("/api/db/tables")
        self.assertEqual(response.status_code, 200, response.text)
        names = {table["name"] for table in response.json()["tables"]}
        self.assertIn("incidents", names)
        self.assertIn("settings", names)
        self.assertNotIn("private_table", names)
        self.assertTrue(all(not name.startswith("sqlite_") for name in names))

    def test_table_query_is_parameterized_and_redacts_sensitive_columns(self) -> None:
        response = self.client.get(
            "/api/db/tables/incident_logs",
            params={"q": "Service", "limit": 20},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        injection = self.client.get(
            "/api/db/tables/incident_logs",
            params={"q": "' OR 1=1 --"},
        )
        self.assertEqual(injection.status_code, 200)
        self.assertEqual(injection.json()["total"], 0)
        too_many = self.client.get("/api/db/tables/incidents?limit=201")
        self.assertEqual(too_many.status_code, 422)
        arbitrary = self.client.get("/api/db/tables/private_table")
        self.assertEqual(arbitrary.status_code, 404)

        evidence = self.client.get("/api/db/tables/emergency_cases")
        self.assertEqual(evidence.json()["rows"][0]["evidence_path"], "[REDACTED]")

    def test_schema_returns_only_allowlisted_ddl(self) -> None:
        response = self.client.get("/api/db/schema")
        self.assertEqual(response.status_code, 200, response.text)
        ddl = {item["name"]: item["createSql"] for item in response.json()["tables"]}
        self.assertIn("incidents", ddl)
        self.assertIn("settings", ddl)
        self.assertNotIn("private_table", ddl)

    def test_export_stream_is_capped_and_redacts_sensitive_data(self) -> None:
        with patch("backend.routers.db_inspector.EXPORT_ROW_CAP", 2):
            response = self.client.get("/api/db/export")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("application/json"))
        body = json.loads(response.text)
        self.assertEqual(body["rowCap"], 2)
        self.assertEqual(body["rowCount"], 2)
        self.assertTrue(body["truncated"])
        self.assertIn("settings", body["tables"])

    def test_export_redacts_sensitive_column_values(self) -> None:
        response = self.client.get("/api/db/export")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("secret-value", response.text)
        self.assertNotIn("uploads/private-file.png", response.text)
        body = json.loads(response.text)
        emergency = body["tables"]["emergency_cases"][0]
        self.assertEqual(emergency["evidence_path"], "[REDACTED]")
        self.assertEqual(
            body["tables"]["settings"][0]["webhook_url"],
            "https://hooks.example/notify?[REDACTED]",
        )

    def test_connection_uses_sqlite_read_only_mode(self) -> None:
        with patch.object(settings, "database_url", f"sqlite:///{self.db_path}"):
            connection = _readonly_connection()
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, "readonly|read-only"):
                connection.execute("CREATE TABLE forbidden (value TEXT)")
        finally:
            connection.close()

    def test_markdown_export_matches_frontend_report_sections_with_database_metrics(self) -> None:
        response = self.client.get("/api/incidents/export.md")
        self.assertEqual(response.status_code, 200)
        report = response.text
        for heading in (
            "# OpsPilot Day 5 Demo Report",
            "## Executive Summary",
            "## Incidents Post-Mortem Log",
            "### INC-101: CRASH on api:5002",
            "- **Telemetry Logs**:",
            "Generated by OpsPilot Telemetry Core Daemon v1.2.4",
        ):
            self.assertIn(heading, report)
        self.assertIn("Autonomous Healing Rate: 100.0%", report)
        self.assertIn("Service recovered", report)
        self.assertNotIn("Average MTTD: 2.8s", report)
        self.assertNotIn("Average MTTR: 1.6s", report)


if __name__ == "__main__":
    unittest.main()
