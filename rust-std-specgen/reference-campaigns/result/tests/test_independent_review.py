from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import independent_review


@dataclass
class _RunnerOptions:
    inactivity_callback: Any | None = None
    watchdog_soft_idle_seconds: float | None = None


class IndependentReviewTests(unittest.TestCase):
    def test_quiet_live_worker_emits_process_liveness_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            run_dir = Path(temporary_directory)
            status_path = run_dir / "status.json"
            result_path = run_dir / "result.json"
            progress_path = run_dir / "progress.jsonl"
            status = {
                "state": "running",
                "updated_at": 1.0,
                "stream_events": 0,
            }
            independent_review.write_json_atomic(status_path, status)
            progress_path.touch()
            protocol = independent_review._ReviewRunProtocol(
                stop_path=run_dir / "STOP",
                status_path=status_path,
                result_path=result_path,
                progress_path=progress_path,
                status=status,
                started_at=1.0,
                heartbeat_interval_seconds=0.0,
            )

            class QuietBackend:
                def run_exec(
                    self,
                    *,
                    prompt: str,
                    options: _RunnerOptions,
                    run_label: str,
                    resume_thread_id: str | None = None,
                ) -> str:
                    self.call = (
                        prompt,
                        run_label,
                        resume_thread_id,
                    )
                    self.options = options
                    options.inactivity_callback(
                        SimpleNamespace(idle_seconds=20.25)
                    )
                    options.inactivity_callback(
                        SimpleNamespace(idle_seconds=40.5)
                    )
                    return "finished"

            quiet_backend = QuietBackend()
            backend = independent_review._LivenessBackend(
                quiet_backend,
                inactivity_callback=protocol.process_liveness,
                heartbeat_interval_seconds=0.01,
            )

            result = backend.run_exec(
                prompt="review",
                options=_RunnerOptions(),
                run_label="reviewer",
            )

            self.assertEqual(result, "finished")
            self.assertEqual(
                quiet_backend.options.watchdog_soft_idle_seconds, 0.01
            )
            written_status = json.loads(status_path.read_text())
            self.assertEqual(written_status["stream_events"], 0)
            self.assertTrue(written_status["worker_alive"])
            self.assertEqual(
                written_status["heartbeat_source"], "process_liveness"
            )
            self.assertEqual(written_status["worker_idle_seconds"], 40.5)
            progress = [
                json.loads(line) for line in progress_path.read_text().splitlines()
            ]
            self.assertEqual(len(progress), 2)
            self.assertTrue(
                all(row["event"] == "heartbeat" for row in progress)
            )
            self.assertTrue(
                all(row["source"] == "process_liveness" for row in progress)
            )
            self.assertTrue(all(row["worker_alive"] for row in progress))
            self.assertEqual(
                [row["worker_idle_seconds"] for row in progress],
                [20.2, 40.5],
            )

    def test_supervised_stop_rejects_late_reviewer_decision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            run_dir = root / "run"
            request_path = root / "request.json"
            review_record_path = root / "review.json"
            request_path.write_text('{"request": "frozen"}\n')
            handoff_writer = mock.Mock()

            class FakeAgentCliBackend:
                def __init__(self, **kwargs: Any) -> None:
                    self.interrupt_reason = kwargs[
                        "default_interrupt_reason_provider"
                    ]
                    self.stream_event = kwargs["event_callback"]

                def run_exec(
                    self,
                    *,
                    prompt: str,
                    options: _RunnerOptions,
                    run_label: str,
                    resume_thread_id: str | None = None,
                ) -> object:
                    options.inactivity_callback(
                        SimpleNamespace(idle_seconds=20.0)
                    )
                    (run_dir / "STOP").touch()
                    self.stream_event("stdout", "late reviewer output")
                    self.observed_interrupt = self.interrupt_reason()
                    return object()

            class FakeReviewer:
                def __init__(self, runner: Any, **_kwargs: Any) -> None:
                    self.runner = runner

                def evaluate(self, **_kwargs: Any) -> SimpleNamespace:
                    self.runner.run_exec(
                        prompt="review",
                        options=_RunnerOptions(),
                        run_label="reviewer",
                    )
                    return SimpleNamespace(
                        status="done",
                        reason="late decision must not be accepted",
                    )

            class FakeReviewerConfig:
                def __init__(self, **kwargs: Any) -> None:
                    self.__dict__.update(kwargs)

            stage = {
                "request": request_path,
                "record": review_record_path,
                "required_terms": {},
                "summary": "summary",
                "objective": "objective",
                "acceptance_language": "acceptance",
            }
            with (
                mock.patch.dict(
                    independent_review.STAGES,
                    {"implementation": stage},
                    clear=True,
                ),
                mock.patch.object(
                    independent_review,
                    "_stage_preconditions",
                    return_value={"proofs": {"path": "proofs", "sha256": "a"}},
                ),
                mock.patch.object(
                    independent_review, "latest_round", return_value=29
                ),
                mock.patch.object(
                    independent_review.aggregate_seal,
                    "CAMPAIGN_ROOT",
                    root,
                ),
                mock.patch.object(
                    independent_review,
                    "_load_reviewer_components",
                    return_value=(
                        FakeAgentCliBackend,
                        FakeReviewer,
                        FakeReviewerConfig,
                        handoff_writer,
                    ),
                ),
            ):
                exit_code = independent_review.main(
                    [
                        "--stage",
                        "implementation",
                        "--task-id",
                        "quiet-stop",
                        "--run-dir",
                        str(run_dir),
                    ]
                )

            self.assertEqual(exit_code, 130)
            handoff_writer.assert_not_called()
            self.assertFalse(review_record_path.exists())
            result = json.loads((run_dir / "result.json").read_text())
            status = json.loads((run_dir / "status.json").read_text())
            self.assertEqual(result["state"], "stopped")
            self.assertFalse(result["acceptance_eligible"])
            self.assertNotIn("canonical_handoff", result)
            self.assertEqual(status["state"], "stopped")
            self.assertFalse(status["worker_alive"])
            progress = [
                json.loads(line)
                for line in (run_dir / "progress.jsonl").read_text().splitlines()
            ]
            self.assertEqual(
                [row["event"] for row in progress],
                ["run_started", "heartbeat", "run_stopped"],
            )
            self.assertEqual(progress[1]["source"], "process_liveness")
            self.assertEqual(status["stream_events"], 0)


if __name__ == "__main__":
    unittest.main()
