#!/usr/bin/env python3
"""Run seeded Result feedback under the live experiment protocol."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import sys
import threading
import time
from typing import Any, TextIO

sys.path.insert(0, str(Path(__file__).resolve().parent))

import specification_support as support


RUNNER = support.ROOT.parent / "run_rust_std_spec_feedback.py"
ADAPTER = support.FEEDBACK_ADAPTER_PATH
VSTD_ROOT = (
    support.ROOT
    / "provenance"
    / "vstd-dependency-closure"
    / "source"
    / "vstd"
)
VERUS_BIN = (
    support.ROOT.parent
    / "verus"
    / "source"
    / "target-verus"
    / "release"
    / "verus"
)
Z3_PATH = support.ROOT.parent / "verus" / "source" / "z3"
LIVE_ROOT = support.VERIFICATION_ROOT / "live_runs"
PROGRESS_PATTERN = re.compile(r"^\[(\d+)/(\d+)\]\s+(.+?)\s+decision=")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fsync_text(stream: TextIO, text: str) -> None:
    stream.write(text)
    stream.flush()
    os.fsync(stream.fileno())


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


class Protocol:
    def __init__(self, run_dir: Path, run_id: str, total: int) -> None:
        self.run_dir = run_dir
        self.run_id = run_id
        self.total = total
        self.done = 0
        self.current: str | None = None
        self.started_at = now()
        self.progress = (run_dir / "progress.jsonl").open(
            "a", encoding="utf-8"
        )
        self.results = (run_dir / "run_results.jsonl").open(
            "a", encoding="utf-8"
        )

    def status(self, state: str, message: str = "") -> None:
        atomic_json(
            self.run_dir / "status.json",
            {
                "current_item": self.current,
                "done": self.done,
                "message": message,
                "run_id": self.run_id,
                "started_at": self.started_at,
                "status": state,
                "total": self.total,
                "updated_at": now(),
            },
        )

    def event(self, event: str, **values: Any) -> None:
        record = {
            "done": self.done,
            "event": event,
            "phase": "feedback_determinism",
            "protocol": "rust_std_result_specification",
            "run_id": self.run_id,
            "total": self.total,
            "ts": now(),
            **values,
        }
        fsync_text(
            self.progress,
            json.dumps(record, sort_keys=True) + "\n",
        )

    def result(self, value: dict[str, Any]) -> None:
        fsync_text(
            self.results,
            json.dumps(value, sort_keys=True) + "\n",
        )

    def close(self) -> None:
        self.progress.close()
        self.results.close()


def reader(
    name: str,
    stream: TextIO,
    messages: queue.Queue[tuple[str, str | None]],
) -> None:
    try:
        for line in stream:
            messages.put((name, line))
    finally:
        messages.put((name, None))


def terminate(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def source_snapshot() -> dict[str, str]:
    equivalence = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
    return {
        "contract_sha256": support.sha256(support.CONTRACT_PATH),
        "feedback_adapter_sha256": support.sha256(ADAPTER),
        "feedback_manifest_sha256": support.sha256(
            support.FEEDBACK_MANIFEST_PATH
        ),
        "feedback_runner_sha256": support.sha256(RUNNER),
        "feedback_worker_sha256": support.sha256(Path(__file__)),
        "outcome_equivalence_sha256": support.sha256(
            support.OUTCOME_EQUIVALENCE_PATH
        ),
        "outcome_equivalence_version_set_sha256": equivalence[
            "version_set_sha256"
        ],
        "relation_capability_sha256": support.sha256(
            support.FEEDBACK_RELATION_CAPABILITY_PATH
        ),
        "seed_candidates_sha256": support.sha256(
            support.FEEDBACK_SEED_PATH
        ),
        "verus_binary_sha256": support.sha256(VERUS_BIN),
        "vstd_closure_manifest_sha256": support.sha256(
            support.ROOT / "provenance" / "vstd_dependency_closure.json"
        ),
        "vstd_context_sha256": support.sha256(
            support.VSTD_CONTRACTS_PATH
        ),
        "vocabulary_sha256": support.sha256(support.VOCABULARY_PATH),
        "z3_binary_sha256": support.sha256(Z3_PATH),
    }


def main() -> int:
    args = parse_args()
    run_id = str(args.run_id)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]+", run_id):
        raise SystemExit("run id contains unsupported characters")
    run_dir = LIVE_ROOT / run_id
    managed_names = {
        "manifest.json",
        "pid",
        "progress.jsonl",
        "run_results.jsonl",
        "status.json",
        "stderr.log",
        "stdout.log",
    }
    if run_dir.exists() and any(
        (run_dir / name).exists() for name in managed_names
    ):
        raise SystemExit(f"run directory has retained worker state: {run_dir}")
    if support.FEEDBACK_ROOT.exists():
        raise SystemExit(
            f"feedback output already exists: {support.FEEDBACK_ROOT}"
        )
    manifest = support.load_json(support.FEEDBACK_MANIFEST_PATH)
    targets = manifest.get("targets")
    inventory = support.inventory_by_id()
    expected_targets = {
        str(inventory[item_id]["target"])
        for item_id in support.generated_ids()
    }
    actual_targets = (
        {
            str(target.get("target"))
            for target in targets
            if isinstance(target, dict)
        }
        if isinstance(targets, list)
        else set()
    )
    if (
        not isinstance(targets, list)
        or len(actual_targets) != len(targets)
        or actual_targets != expected_targets
    ):
        raise SystemExit(
            "feedback manifest target set does not match generated inventory"
        )
    target_count = len(expected_targets)
    command = [
        sys.executable,
        str(ADAPTER),
        "--runner",
        str(RUNNER),
        "--manifest",
        str(support.FEEDBACK_MANIFEST_PATH),
        "--contracts",
        str(support.VSTD_CONTRACTS_PATH),
        "--vstd-root",
        str(VSTD_ROOT),
        "--verus-bin",
        str(VERUS_BIN),
        "--z3-path",
        str(Z3_PATH),
        "--out",
        str(support.FEEDBACK_ROOT),
        "--seed-candidates",
        str(support.FEEDBACK_SEED_PATH),
        "--outcome-equivalence",
        str(support.OUTCOME_EQUIVALENCE_PATH),
        "--relation-capability",
        str(support.FEEDBACK_RELATION_CAPABILITY_PATH),
        "--feedback-rounds",
        "0",
        "--jobs",
        "4",
        "--check-timeout",
        "240",
        "--rlimit",
        "60",
    ]
    run_dir.mkdir(parents=True, exist_ok=True)
    for filename in (
        "stdout.log",
        "stderr.log",
        "progress.jsonl",
        "run_results.jsonl",
    ):
        (run_dir / filename).touch()
    (run_dir / "pid").write_text(f"{os.getpid()}\n", encoding="ascii")
    run_manifest = {
        "budget": {
            "check_timeout_seconds_per_call": 240,
            "feedback_rounds": 0,
            "jobs": 4,
            "model_calls": 0,
            "rlimit": 60,
        },
        "command": command,
        "created_at_utc": now(),
        "expected_trials": target_count,
        "model_routes": ["seeded candidates; no model/API calls"],
        "objective": (
            "Typecheck every generated core::result contract, retain the "
            "canonical determinism diagnostic, and bind the explicit "
            "unsupported classification for selected-relation evaluation."
        ),
        "output_root": str(support.FEEDBACK_ROOT),
        "run_id": run_id,
        "source_snapshot": source_snapshot(),
    }
    atomic_json(run_dir / "manifest.json", run_manifest)
    protocol = Protocol(run_dir, run_id, target_count)
    protocol.status("pending")
    protocol.event(
        "run_started", message="launching canonical feedback runner"
    )
    for target in targets:
        protocol.event(
            "trial_started",
            status="queued",
            task_id=str(target["target"]),
        )
    protocol.status("running")

    stdout_log = (run_dir / "stdout.log").open("a", encoding="utf-8")
    stderr_log = (run_dir / "stderr.log").open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=support.ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    messages: queue.Queue[tuple[str, str | None]] = queue.Queue()
    threads = [
        threading.Thread(
            target=reader,
            args=("stdout", process.stdout, messages),
            daemon=True,
        ),
        threading.Thread(
            target=reader,
            args=("stderr", process.stderr, messages),
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    closed_streams: set[str] = set()
    last_heartbeat = time.monotonic()
    cancelled = False
    try:
        while process.poll() is None or len(closed_streams) < 2:
            if (run_dir / "STOP").exists() and process.poll() is None:
                cancelled = True
                protocol.event(
                    "early_stop",
                    reason="STOP file observed",
                    status="cancelled",
                )
                terminate(process)
            try:
                stream_name, line = messages.get(timeout=1)
            except queue.Empty:
                stream_name, line = "", None
            if stream_name and line is None:
                closed_streams.add(stream_name)
            elif line is not None:
                destination = (
                    stdout_log
                    if stream_name == "stdout"
                    else stderr_log
                )
                fsync_text(destination, line)
                if stream_name == "stdout":
                    match = PROGRESS_PATTERN.match(line.strip())
                    if match is not None:
                        protocol.done = int(match.group(1))
                        protocol.current = match.group(3)
                        protocol.result(
                            {
                                "done": protocol.done,
                                "run_id": run_id,
                                "target": protocol.current,
                                "total": int(match.group(2)),
                                "ts": now(),
                            }
                        )
                        protocol.event(
                            "trial_done",
                            status="completed",
                            task_id=protocol.current,
                        )
                        protocol.status("running")
            if time.monotonic() - last_heartbeat >= 20:
                protocol.event(
                    "heartbeat",
                    message="feedback runner remains active",
                    task_id=protocol.current,
                )
                protocol.status("running")
                last_heartbeat = time.monotonic()
    finally:
        stdout_log.close()
        stderr_log.close()

    return_code = process.wait()
    if cancelled:
        protocol.event("run_cancelled", status="cancelled")
        protocol.status("cancelled", "STOP file observed")
        protocol.close()
        return 130
    if return_code != 0:
        protocol.event(
            "run_failed",
            status="failed",
            message=f"feedback runner exited {return_code}",
        )
        protocol.status("failed", f"feedback runner exited {return_code}")
        protocol.close()
        return return_code
    if not support.FEEDBACK_SUMMARY_PATH.is_file():
        protocol.event(
            "run_failed",
            status="failed",
            message="batch summary missing",
        )
        protocol.status("failed", "batch summary missing")
        protocol.close()
        return 1
    summary = support.load_json(support.FEEDBACK_SUMMARY_PATH)
    counts = summary.get("counts", {})
    equivalence = support.load_json(support.OUTCOME_EQUIVALENCE_PATH)
    equivalence_binding = (
        support.outcome_equivalence_artifact_binding(equivalence)
    )
    relation_capability = support.load_json(
        support.FEEDBACK_RELATION_CAPABILITY_PATH
    )
    relation_capability_binding = (
        support.feedback_relation_capability_binding(
            relation_capability
        )
    )
    diagnostic_bindings = support.feedback_diagnostic_binding_set()
    if (
        counts.get("targets") != target_count
        or counts.get("missing_targets") != 0
        or counts.get("extra_targets") != 0
        or counts.get("equivalence_bound_targets") != target_count
        or counts.get("selected_relation_evaluated_targets") != 0
        or counts.get("selected_relation_unsupported_targets")
        != target_count
        or counts.get("diagnostic_only_rounds")
        != diagnostic_bindings["binding_count"]
        or diagnostic_bindings["binding_count"] < target_count
        or summary.get("outcome_equivalence") != equivalence_binding
        or summary.get("selected_relation_evaluation")
        != relation_capability_binding
        or summary.get("canonical_diagnostic_bindings")
        != diagnostic_bindings
    ):
        protocol.event(
            "run_failed",
            status="failed",
            message="feedback target reconciliation failed",
        )
        protocol.status("failed", "feedback target reconciliation failed")
        protocol.close()
        return 1
    support.write_json(
        support.FEEDBACK_RUN_BINDING_PATH,
        {
            "equivalence_bound_target_count": target_count,
            "canonical_diagnostic_bindings": diagnostic_bindings,
            "outcome_equivalence": equivalence_binding,
            "selected_relation_evaluation": relation_capability_binding,
            "run_id": run_id,
            "run_manifest_path": str(
                (run_dir / "manifest.json").relative_to(support.ROOT)
            ),
            "run_manifest_sha256": support.sha256(
                run_dir / "manifest.json"
            ),
            "schema_version": 3,
            "status": "completed",
            "summary_path": str(
                support.FEEDBACK_SUMMARY_PATH.relative_to(support.ROOT)
            ),
            "summary_sha256": support.sha256(
                support.FEEDBACK_SUMMARY_PATH
            ),
        },
    )
    protocol.done = target_count
    protocol.current = None
    protocol.event(
        "run_completed",
        status="completed",
        message="all feedback targets produced results",
    )
    protocol.status("completed", "all feedback targets produced results")
    protocol.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
