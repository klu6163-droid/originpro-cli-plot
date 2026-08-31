from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[1]


def load_script(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SKILL_ROOT / "scripts" / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


build = load_script("originpro_build_tested", "originpro_build.py")
runner = load_script("make_user_runner_tested", "make_user_runner.py")


class BackendRoutingTests(unittest.TestCase):
    def test_auto_falls_back_only_when_cli_backend_is_unavailable(self) -> None:
        with (
            mock.patch.object(
                build,
                "run_origin_cli_worker",
                side_effect=build.BackendUnavailable("CLI worker never started"),
            ) as cli,
            mock.patch.object(
                build,
                "running_origin_processes",
                return_value=[],
            ),
            mock.patch.object(
                build,
                "execute_job_com",
                return_value={"backend": "originpro-com-python"},
            ) as com,
        ):
            result = build.run_selected_backend({}, "build", "auto", None, 30, 5, False)

        cli.assert_called_once()
        com.assert_called_once_with({}, False)
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_from"], "cli")
        self.assertIn("never started", result["fallback_reason"])

    def test_auto_does_not_fallback_for_job_errors(self) -> None:
        with (
            mock.patch.object(
                build,
                "run_origin_cli_worker",
                side_effect=build.JobError("invalid plot"),
            ),
            mock.patch.object(build, "execute_job_com") as com,
        ):
            with self.assertRaisesRegex(build.JobError, "invalid plot"):
                build.run_selected_backend({}, "build", "auto", None, 30, 5, False)
        com.assert_not_called()

    def test_auto_refuses_fallback_if_origin_remains(self) -> None:
        with (
            mock.patch.object(
                build,
                "run_origin_cli_worker",
                side_effect=build.BackendUnavailable("CLI worker never started"),
            ),
            mock.patch.object(
                build,
                "running_origin_processes",
                return_value=['"Origin64.exe","123"'],
            ),
            mock.patch.object(build, "execute_job_com") as com,
        ):
            with self.assertRaisesRegex(build.JobError, "fallback refused"):
                build.run_selected_backend({}, "build", "auto", None, 30, 5, False)
        com.assert_not_called()


class RunnerGenerationTests(unittest.TestCase):
    def test_runner_accepts_multiple_jobs_and_uses_auto_backend(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jobs = [root / "job_c.json", root / "job_o.json"]
            for job in jobs:
                job.write_text("{}", encoding="utf-8")
            output = root / "run_all.cmd"
            arguments = [
                "make_user_runner.py",
                "--job",
                str(jobs[0]),
                "--job",
                str(jobs[1]),
                "--output",
                str(output),
                "--backend",
                "auto",
                "--timeout",
                "40",
                "--cli-startup-timeout",
                "12",
            ]
            with mock.patch.object(sys, "argv", arguments):
                self.assertEqual(runner.main(), 0)

            text = output.read_text(encoding="utf-8-sig")
            self.assertEqual(text.count(str(jobs[0].resolve())), 2)
            self.assertEqual(text.count(str(jobs[1].resolve())), 2)
            self.assertEqual(text.count("--backend auto"), 4)
            self.assertEqual(text.count("pause"), 2)
            self.assertIn("2 Origin project(s) created and verified.", text)
            self.assertIn("--cli-startup-timeout 12", text)


if __name__ == "__main__":
    unittest.main()
