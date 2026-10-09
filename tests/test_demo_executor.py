import asyncio
import contextlib
import io
import sys
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.config import Settings
from backend.errors import AppError
from backend.models import Base
from backend.services.executor import (
    ChaosAction,
    DemoService,
    DemoTarget,
    FixAction,
    execute_chaos,
    execute_fix,
)


class DemoTargetValidationTests(unittest.TestCase):
    def test_malicious_service_name_is_rejected_before_subprocess(self) -> None:
        with patch("backend.services.executor.subprocess.run") as run:
            with self.assertRaises(ValueError):
                DemoTarget("api; rm -rf /", 5002)  # type: ignore[arg-type]
            run.assert_not_called()

    def test_port_22_is_rejected_before_subprocess(self) -> None:
        with patch("backend.services.executor.subprocess.run") as run:
            with self.assertRaises(ValueError):
                DemoTarget(DemoService.API, 22)
            run.assert_not_called()

    def test_non_loopback_host_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DemoTarget(DemoService.API, 5002, "0.0.0.0")

    def test_cli_target_parser_rejects_malicious_names_without_http(self) -> None:
        import backend.scripts.inject as inject

        with (
            patch.object(sys, "argv", ["inject.py", "crash", "--target", "api; rm -rf /:5002"]),
            patch("urllib.request.urlopen") as urlopen,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(inject.main(), 2)
            urlopen.assert_not_called()

    def test_cli_target_parser_rejects_unlisted_port_without_http(self) -> None:
        import backend.scripts.fixer as fixer

        with (
            patch.object(sys, "argv", ["fixer.py", "restart", "--target", "api:22"]),
            patch("urllib.request.urlopen") as urlopen,
            contextlib.redirect_stderr(io.StringIO()),
        ):
            self.assertEqual(fixer.main(), 2)
            urlopen.assert_not_called()


class ExecutorGateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = Session(self.engine)

    def tearDown(self) -> None:
        self.db.close()
        self.engine.dispose()

    async def test_chaos_disabled_rejects_before_process_start(self) -> None:
        with patch("backend.services.executor.subprocess.run") as run:
            with self.assertRaises(AppError) as raised:
                await execute_chaos(
                    ChaosAction.CRASH,
                    DemoTarget(DemoService.API, 5002),
                    config=Settings(_env_file=None, chaos_enabled=False),
                )
            self.assertEqual(raised.exception.code, "CHAOS_DISABLED")
            run.assert_not_called()

    async def test_fixer_requires_registered_demo_target(self) -> None:
        with patch("backend.services.executor.subprocess.run") as run:
            with self.assertRaises(AppError) as raised:
                await execute_fix(
                    FixAction.RESTART,
                    DemoTarget(DemoService.API, 5002),
                    self.db,
                )
            self.assertEqual(raised.exception.code, "DEMO_TARGET_NOT_REGISTERED")
            run.assert_not_called()

    async def test_fix_runs_only_after_demo_registration(self) -> None:
        from backend.models import Endpoint

        self.db.add(
            Endpoint(
                name="api-demo",
                url="http://127.0.0.1:5002",
                service_key="api",
                port=5002,
                enabled=True,
                is_demo_target=True,
            )
        )
        self.db.commit()
        with patch(
            "backend.services.executor.subprocess.run",
            return_value=type("Completed", (), {"returncode": 0, "stdout": '{"status":"ok"}'})(),
        ) as run:
            result = await execute_fix(
                FixAction.RESTART,
                DemoTarget(DemoService.API, 5002),
                self.db,
            )
            self.assertTrue(result.ok)
            args, kwargs = run.call_args
            self.assertEqual(args[0][2:], ["restart", "--target", "api:5002"])
            self.assertFalse(kwargs["shell"])
            self.assertEqual(kwargs["timeout"], 10)
            self.assertTrue(kwargs["capture_output"])


if __name__ == "__main__":
    unittest.main()
