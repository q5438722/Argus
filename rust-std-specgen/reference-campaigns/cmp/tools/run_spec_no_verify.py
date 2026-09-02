#!/usr/bin/env python3
"""Run and retain the generated specification Verus --no-verify gate."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

CAMPAIGN_ROOT = Path(__file__).resolve().parents[1]
if str(CAMPAIGN_ROOT) not in sys.path:
    sys.path.insert(0, str(CAMPAIGN_ROOT))

from tools import build_specification as builder


ROOT = builder.ROOT
EVIDENCE_ROOT = (
    ROOT / "verification" / "evidence" / "specification-no-verify"
)
VERUS = ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
Z3 = ROOT.parent / "verus" / "source" / "z3"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    data = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(data, encoding="utf-8")
    os.replace(temporary, path)


def event(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def update_status(
    path: Path,
    *,
    run_id: str,
    status: str,
    done: int,
    current: str,
    started_at: str,
) -> None:
    atomic_json(
        path,
        {
            "run_id": run_id,
            "status": status,
            "done": done,
            "total": 1,
            "current": current,
            "started_at": started_at,
            "updated_at": now(),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()
    run_id = args.run_id
    if not re_valid_run_id(run_id):
        raise SystemExit("run id must contain only letters, digits, dot, dash, or underscore")
    run_dir = EVIDENCE_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    progress = run_dir / "progress.jsonl"
    stdout_path = run_dir / "stdout.log"
    stderr_path = run_dir / "stderr.log"
    status_path = run_dir / "status.json"
    stdout_path.touch()
    stderr_path.touch()
    progress.touch()

    relative_contract = "specs/generated_cmp_specs.rs"
    command = [
        str(VERUS),
        relative_contract,
        "--crate-type=lib",
        "--no-verify",
    ]
    source_snapshot = {
        "contract_sha256": sha256(builder.GENERATED),
        "inventory_sha256": sha256(builder.INVENTORY),
        "vocabulary_sha256": sha256(builder.VOCABULARY),
        "verus_binary_sha256": sha256(VERUS),
        "z3_sha256": sha256(Z3),
    }
    manifest = {
        "schema_version": 1,
        "run_id": run_id,
        "objective": "Verus typecheck of all generated core::cmp contracts",
        "command": command,
        "expected_trials": 1,
        "model_routes": [],
        "budget": {"subprocesses": 1},
        "source_snapshot": source_snapshot,
        "working_directory": str(ROOT),
    }
    atomic_json(run_dir / "manifest.json", manifest)
    started_at = now()
    update_status(
        status_path,
        run_id=run_id,
        status="pending",
        done=0,
        current=relative_contract,
        started_at=started_at,
    )
    if (run_dir / "STOP").exists():
        event(
            progress,
            {
                "ts": now(),
                "event": "run_cancelled",
                "run_id": run_id,
                "done": 0,
                "total": 1,
                "phase": "no_verify",
                "protocol": "verus_specification_typecheck",
                "task_id": relative_contract,
                "status": "cancelled",
                "message": "STOP present before launch",
            },
        )
        update_status(
            status_path,
            run_id=run_id,
            status="cancelled",
            done=0,
            current=relative_contract,
            started_at=started_at,
        )
        return 130
    common = {
        "run_id": run_id,
        "done": 0,
        "total": 1,
        "phase": "no_verify",
        "protocol": "verus_specification_typecheck",
        "task_id": relative_contract,
    }
    event(
        progress,
        {
            **common,
            "ts": now(),
            "event": "run_started",
            "status": "running",
            "message": "retained Verus no-verify run started",
        },
    )
    event(
        progress,
        {
            **common,
            "ts": now(),
            "event": "trial_started",
            "status": "running",
            "message": "generated specification crate",
        },
    )
    update_status(
        status_path,
        run_id=run_id,
        status="running",
        done=0,
        current=relative_contract,
        started_at=started_at,
    )
    started = time.monotonic()
    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(Z3)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=stdout,
            stderr=stderr,
        )
        (run_dir / "pid").write_text(f"{process.pid}\n", encoding="utf-8")
        exit_code = process.wait()
    duration_ms = int((time.monotonic() - started) * 1000)
    passed = exit_code == 0
    terminal = "completed" if passed else "failed"
    trial_event = "trial_done" if passed else "trial_failed"
    event(
        progress,
        {
            **common,
            "ts": now(),
            "event": trial_event,
            "done": 1,
            "status": "passed" if passed else "failed",
            "message": f"Verus exited {exit_code}",
        },
    )
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "status": "passed" if passed else "failed",
        "exit_code": exit_code,
        "duration_ms": duration_ms,
        "command": command,
        "inputs": source_snapshot,
        "stdout_sha256": sha256(stdout_path),
        "stderr_sha256": sha256(stderr_path),
    }
    atomic_json(run_dir / "result.json", result)
    event(
        progress,
        {
            **common,
            "ts": now(),
            "event": "run_completed" if passed else "run_failed",
            "done": 1,
            "status": terminal,
            "message": f"retained result status={result['status']}",
        },
    )
    update_status(
        status_path,
        run_id=run_id,
        status=terminal,
        done=1,
        current="",
        started_at=started_at,
    )
    atomic_json(
        EVIDENCE_ROOT / "latest.json",
        {
            "run_id": run_id,
            "run_dir": str(run_dir.relative_to(ROOT)),
            "result_sha256": sha256(run_dir / "result.json"),
        },
    )
    print(json.dumps(result, sort_keys=True))
    return exit_code


def re_valid_run_id(value: str) -> bool:
    return bool(value) and all(
        character.isalnum() or character in "._-" for character in value
    )


if __name__ == "__main__":
    raise SystemExit(main())
