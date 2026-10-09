import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.models import (
    Analysis,
    Base,
    Endpoint,
    Incident,
    IncidentLog,
    ProbeResult,
    Remediation,
    RuntimeSettings,
    utc_now,
)
from backend.main import lifespan
from backend.services.executor import ExecutionResult
from backend.services.monitor import _classify_anomaly, _store_probe
from backend.services.pipeline import (
    create_injected_incident,
    process_detected_anomaly,
)
from backend.services.probe import Probe


class MonitorClassificationTests(unittest.TestCase):
    def test_crash_cpu_and_debounced_latency_classification(self) -> None:
        healthy = Probe(200, 1001, True, utc_now(), cpu_percent=2)
        self.assertIsNone(_classify_anomaly(healthy, 1000, 1))
        self.assertEqual(_classify_anomaly(healthy, 1000, 2), "LATENCY")
        self.assertEqual(
            _classify_anomaly(
                Probe(200, 10, True, utc_now(), cpu_percent=90.1),
                1000,
                0,
            ),
            "CPU_SPIKE",
        )
        self.assertEqual(_classify_anomaly(Probe(None, 1, False, utc_now()), 1000, 0), "CRASH")

    def test_probe_history_is_pruned_to_latest_thousand(self) -> None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(engine)
        factory = Session
        with factory(engine) as db:
            endpoint = Endpoint(name="web", url="http://127.0.0.1:5001")
            db.add(endpoint)
            db.commit()
            endpoint_id = endpoint.id
            db.add_all(
                ProbeResult(
                    endpoint_id=endpoint_id,
                    http_status=200,
                    ping_latency_ms=1,
                    ok=True,
                    checked_at=utc_now(),
                )
                for _ in range(1000)
            )
            db.commit()
        with patch("backend.services.monitor.SessionLocal", side_effect=lambda: factory(engine)) as _:
            _store_probe(endpoint_id, Probe(200, 2, True, utc_now()))
        with factory(engine) as db:
            rows = db.scalars(
                select(ProbeResult).where(ProbeResult.endpoint_id == endpoint_id)
            ).all()
            self.assertEqual(len(rows), 1000)
        engine.dispose()


class MonitorLifecycleTests(unittest.IsolatedAsyncioTestCase):
    async def test_lifespan_starts_monitor_only_when_enabled(self) -> None:
        async def idle_monitor() -> None:
            await asyncio.Event().wait()

        disabled_app = SimpleNamespace(state=SimpleNamespace())
        with (
            patch("backend.main.create_all"),
            patch("backend.main.settings.monitor_enabled", False),
        ):
            async with lifespan(disabled_app):
                self.assertFalse(hasattr(disabled_app.state, "monitor_task"))

        enabled_app = SimpleNamespace(state=SimpleNamespace())
        with (
            patch("backend.main.create_all"),
            patch("backend.main.settings.monitor_enabled", True),
            patch("backend.services.monitor.monitor_loop", new=idle_monitor),
        ):
            async with lifespan(enabled_app):
                task = enabled_app.state.monitor_task
                self.assertFalse(task.done())
        self.assertTrue(task.cancelled())


class IncidentPipelineTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)
        self.endpoint = Endpoint(
            name="worker",
            url="http://127.0.0.1:5003",
            service_key="worker",
            port=5003,
            enabled=True,
            is_demo_target=True,
        )
        self.db.add(self.endpoint)
        self.db.add(RuntimeSettings(id=1, zero_touch_enabled=False))
        self.db.commit()

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    async def test_detection_attaches_to_injected_incident_and_waits_for_approval(self) -> None:
        incident = create_injected_incident(self.db, self.endpoint, "CPU_SPIKE")
        with patch(
            "backend.services.pipeline._diagnose",
            new_callable=AsyncMock,
        ) as diagnose:
            diagnose.return_value = {
                "rootCause": "CPU spin",
                "confidence": 0.9,
                "severity": "CRIT",
                "recommendedAction": "kill_spinloop",
                "rationale": "CPU metric is above threshold.",
                "llmStatus": "ok",
                "latencyMs": 20,
            }
            returned = await process_detected_anomaly(
                self.db,
                self.endpoint,
                "CPU_SPIKE",
                metrics={"cpu_percent": 98},
                logs=["loop detected"],
            )
        self.assertIsNotNone(returned)
        self.assertEqual(returned.id, incident.id)
        self.assertIsNotNone(returned.detected_at)
        self.assertIsNotNone(returned.diagnosed_at)
        self.assertEqual(returned.status, "awaiting_approval")
        self.assertEqual(len(self.db.scalars(select(Incident)).all()), 1)
        self.assertEqual(len(self.db.scalars(select(Analysis)).all()), 1)
        self.assertTrue(self.db.scalars(select(IncidentLog)).all())
        repeated = await process_detected_anomaly(
            self.db,
            self.endpoint,
            "CPU_SPIKE",
            metrics={"cpu_percent": 98},
        )
        self.assertEqual(repeated.id, incident.id)
        self.assertEqual(len(self.db.scalars(select(Analysis)).all()), 1)

    async def test_zero_touch_runs_fix_in_parallel_and_verifies(self) -> None:
        runtime = self.db.get(RuntimeSettings, 1)
        runtime.zero_touch_enabled = True
        self.db.commit()
        injected = create_injected_incident(self.db, self.endpoint, "CPU_SPIKE")
        fix_started = asyncio.Event()
        diagnosis_finished = asyncio.Event()

        async def fake_fix(*_args, **_kwargs):
            fix_started.set()
            await diagnosis_finished.wait()
            return ExecutionResult(True, None, "stopped", 0.1)

        async def fake_diagnose(*_args, **_kwargs):
            self.assertTrue(fix_started.is_set())
            await asyncio.sleep(0)
            diagnosis_finished.set()
            return {
                "rootCause": "CPU spin",
                "confidence": 0.9,
                "severity": "CRIT",
                "recommendedAction": "kill_spinloop",
                "rationale": "CPU metric is above threshold.",
                "llmStatus": "ok",
                "latencyMs": 20,
            }

        with (
            patch("backend.services.pipeline._execute_registered_fix", side_effect=fake_fix),
            patch(
                "backend.services.pipeline._verify_recovery",
                new_callable=AsyncMock,
            ) as verify,
            patch("backend.services.pipeline._diagnose", side_effect=fake_diagnose),
        ):
            verify.return_value = (True, [])
            returned = await asyncio.wait_for(
                process_detected_anomaly(
                    self.db,
                    self.endpoint,
                    "CPU_SPIKE",
                    incident_id=injected.id,
                    metrics={"cpu_percent": 98},
                ),
                timeout=2,
            )
        self.assertTrue(fix_started.is_set())
        self.assertTrue(diagnosis_finished.is_set())
        self.assertEqual(returned.status, "verified")
        self.assertTrue(returned.auto_healed)
        self.assertIsNotNone(returned.fixed_at)
        self.assertIsNotNone(returned.verified_at)
        remediation = self.db.scalar(select(Remediation))
        self.assertEqual(remediation.executed_by, "auto")
        self.assertTrue(remediation.probe_verified)

    async def test_failed_verification_is_persisted_and_triggers_webhook(self) -> None:
        runtime = self.db.get(RuntimeSettings, 1)
        runtime.zero_touch_enabled = True
        self.db.commit()
        incident = create_injected_incident(self.db, self.endpoint, "CPU_SPIKE")

        async def fake_fix(*_args, **_kwargs):
            return ExecutionResult(True, None, "stopped", 0.1)

        with (
            patch("backend.services.pipeline._execute_registered_fix", side_effect=fake_fix),
            patch(
                "backend.services.pipeline._verify_recovery",
                new_callable=AsyncMock,
                return_value=(False, []),
            ),
            patch(
                "backend.services.pipeline._diagnose",
                new_callable=AsyncMock,
                return_value={
                    "rootCause": "CPU spin",
                    "confidence": 0.9,
                    "severity": "CRIT",
                    "recommendedAction": "kill_spinloop",
                    "rationale": "CPU metric is above threshold.",
                    "llmStatus": "ok",
                    "latencyMs": 20,
                },
            ),
            patch("backend.services.pipeline._fire_webhook") as fire_webhook,
        ):
            returned = await process_detected_anomaly(
                self.db,
                self.endpoint,
                "CPU_SPIKE",
                incident_id=incident.id,
                metrics={"cpu_percent": 98},
            )
        self.assertEqual(returned.status, "failed")
        self.assertFalse(returned.auto_healed)
        self.assertIsNotNone(returned.fixed_at)
        self.assertIsNone(returned.verified_at)
        remediation = self.db.scalar(select(Remediation))
        self.assertFalse(remediation.probe_verified)
        fire_webhook.assert_called_once()


if __name__ == "__main__":
    unittest.main()
