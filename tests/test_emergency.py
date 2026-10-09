import asyncio
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image
from pydantic import SecretStr
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.config import settings
from backend.database import get_db
from backend.main import create_app
from backend.models import Base, EmergencyCase
from backend.services.llm.service import triage_emergency


class _FakeTriageProvider:
    def __init__(self, response: str | Exception) -> None:
        self.response = response
        self.prompt_payload: str | None = None

    async def analyze(self, prompt_payload: str) -> str:
        self.prompt_payload = prompt_payload
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class EmergencyRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)

        def override_get_db():
            with Session(self.engine) as db:
                yield db

        self.app = create_app()
        self.app.dependency_overrides[get_db] = override_get_db
        self.client_context = TestClient(self.app)
        self.client = self.client_context.__enter__()

    def tearDown(self) -> None:
        self.client_context.__exit__(None, None, None)
        self.engine.dispose()

    def _create_case(self) -> str:
        with Session(self.engine) as db:
            case = EmergencyCase(
                case_id="EMG-8192",
                incident_type="Network interruption",
                location="Rack 04",
                priority="RED",
                reported_by="Lead SRE",
                description="Packet loss observed",
                status="Dispatched",
                ai_triage_summary="Critical: escalate immediately to on-call",
                llm_status="failed",
            )
            db.add(case)
            db.commit()
        return "EMG-8192"

    @staticmethod
    def _png_bytes() -> bytes:
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2), color="red").save(buffer, format="PNG")
        return buffer.getvalue()

    @staticmethod
    def _jpeg_with_exif() -> bytes:
        image = Image.new("RGB", (2, 2), color="blue")
        exif = image.getexif()
        exif[270] = "private metadata"
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", exif=exif.tobytes())
        return buffer.getvalue()

    def test_intake_trims_validates_falls_back_and_persists_llm_failure(self) -> None:
        with patch("backend.routers.emergency.publish_event") as publish:
            response = self.client.post(
                "/api/emergency/intake",
                json={
                    "incidentType": "  Network interruption ",
                    "location": " Rack 04 ",
                    "priority": "RED",
                    "reportedBy": " Lead SRE ",
                    "description": " Packet loss observed ",
                },
            )

        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body["status"], "Dispatched")
        self.assertTrue(body["caseId"].startswith("EMG-"))
        self.assertIn("Critical: escalate immediately to on-call", body["aiTriageSummary"])
        self.assertEqual(
            body["safetyNotice"],
            "AI output is decision support only and does not replace professional human evaluation.",
        )
        with Session(self.engine) as db:
            case = db.scalar(select(EmergencyCase).where(EmergencyCase.case_id == body["caseId"]))
            self.assertEqual(case.incident_type, "Network interruption")
            self.assertEqual(case.description, "Packet loss observed")
            self.assertEqual(case.llm_status, "failed")
        publish.assert_called_once()
        self.assertEqual(publish.call_args.kwargs["event_type"], "incident_created")

    def test_intake_rejects_overlong_description(self) -> None:
        response = self.client.post(
            "/api/emergency/intake",
            json={
                "incidentType": "Network interruption",
                "location": "Rack 04",
                "priority": "RED",
                "reportedBy": "Lead SRE",
                "description": "x" * 2001,
            },
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_ERROR")

    def test_evidence_upload_requires_authentication(self) -> None:
        case_id = self._create_case()
        with patch.object(settings, "api_key", SecretStr("test-api-key")):
            response = self.client.post(
                f"/api/emergency/{case_id}/evidence",
                files={"upload": ("evidence.png", self._png_bytes(), "image/png")},
            )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"]["code"], "UNAUTHORIZED")

    def test_oversized_upload_is_rejected_before_image_decoding(self) -> None:
        case_id = self._create_case()
        with patch.object(settings, "api_key", SecretStr("test-api-key")):
            response = self.client.post(
                f"/api/emergency/{case_id}/evidence",
                headers={"X-API-Key": "test-api-key"},
                files={
                    "upload": (
                        "large.png",
                        b"\x89PNG\r\n\x1a\n" + b"x" * (5 * 1024 * 1024),
                        "image/png",
                    )
                },
            )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "EVIDENCE_TOO_LARGE")

    def test_fake_png_extension_is_rejected_by_content(self) -> None:
        case_id = self._create_case()
        with patch.object(settings, "api_key", SecretStr("test-api-key")):
            response = self.client.post(
                f"/api/emergency/{case_id}/evidence",
                headers={"X-API-Key": "test-api-key"},
                files={"upload": ("actually.txt.png", b"not an image", "image/png")},
            )
        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "INVALID_EVIDENCE_IMAGE")

    def test_valid_image_is_reencoded_and_served_only_as_attachment(self) -> None:
        case_id = self._create_case()
        with tempfile.TemporaryDirectory() as upload_dir:
            with (
                patch.object(settings, "api_key", SecretStr("test-api-key")),
                patch("backend.routers.emergency.UPLOAD_ROOT", Path(upload_dir)),
            ):
                upload = self.client.post(
                    f"/api/emergency/{case_id}/evidence",
                    headers={"X-API-Key": "test-api-key"},
                    files={
                        "upload": (
                            "../../private-client-name.png",
                            self._jpeg_with_exif(),
                            "image/jpeg",
                        )
                    },
                )
                self.assertEqual(upload.status_code, 201, upload.text)
                self.assertEqual(upload.json()["contentType"], "image/jpeg")

                with Session(self.engine) as db:
                    case = db.scalar(
                        select(EmergencyCase).where(EmergencyCase.case_id == case_id)
                    )
                    self.assertTrue(case.evidence_path.startswith("uploads/"))
                    filename = Path(case.evidence_path).name
                    self.assertNotIn("private-client-name", filename)
                    stored_image = Image.open(Path(upload_dir) / filename)
                    self.assertEqual(stored_image.getexif(), {})
                    self.assertNotIn("private metadata", stored_image.info.values())

                unauthorized = self.client.get(f"/api/emergency/{case_id}/evidence")
                self.assertEqual(unauthorized.status_code, 401)
                served = self.client.get(
                    f"/api/emergency/{case_id}/evidence",
                    headers={"X-API-Key": "test-api-key"},
                )
                self.assertEqual(served.status_code, 200)
                self.assertEqual(served.headers["x-content-type-options"], "nosniff")
                self.assertIn("attachment", served.headers["content-disposition"])

    def test_triage_uses_redacted_description_and_operational_steps(self) -> None:
        provider = _FakeTriageProvider(
            json.dumps(
                {
                    "summary": "Regional API availability is degraded.",
                    "suggested_next_steps": ["failover", "notify_on_call"],
                }
            )
        )
        from backend.config import Settings

        result = asyncio.run(
            triage_emergency(
                "Investigate contact user@example.com",
                "YELLOW",
                provider=provider,
                config=Settings(_env_file=None, llm_model="test-model"),
            )
        )
        self.assertEqual(result["llmStatus"], "ok")
        self.assertIn("Fail over to a healthy target", result["summary"])
        self.assertNotIn("user@example.com", provider.prompt_payload)

    def test_triage_provider_failure_returns_priority_fallback(self) -> None:
        from backend.config import Settings

        result = asyncio.run(
            triage_emergency(
                "service unavailable",
                "RED",
                provider=_FakeTriageProvider(TimeoutError("provider down")),
                config=Settings(_env_file=None, llm_model="test-model"),
            )
        )
        self.assertEqual(result["llmStatus"], "failed")
        self.assertIn("Critical: escalate immediately to on-call", result["summary"])


if __name__ == "__main__":
    unittest.main()
