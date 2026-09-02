#!/usr/bin/env python3
"""Retain decisive evidence for the loaded-vstd float comparison model gap."""

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


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_ROOT = ROOT / "verification" / "evidence" / "float-model-boundary"
SEMANTICS_PROBE = ROOT / "research" / "float_model_semantics_probe.rs"
OVERRIDE_PROBE = ROOT / "research" / "float_stronger_contract_probe.rs"
DEFAULT_VERUS = (
    ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
)
DEFAULT_Z3 = ROOT.parent / "verus" / "source" / "z3"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(value)
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_bytes(path, json_bytes(value))


def append_jsonl(path: Path, value: Any) -> None:
    with path.open("ab") as stream:
        stream.write(
            json.dumps(value, sort_keys=True).encode() + b"\n"
        )
        stream.flush()
        os.fsync(stream.fileno())


def valid_run_id(value: str) -> bool:
    return bool(value) and all(
        character.isalnum() or character in "._-" for character in value
    )


def run_trial(
    *,
    run_id: str,
    run_dir: Path,
    name: str,
    source: Path,
    mode: str,
    expected_fragment: str,
    done_before: int,
    verus: Path,
    z3: Path,
    timeout: int,
) -> dict[str, Any]:
    command = [str(verus), str(source), "--crate-type=lib"]
    if mode == "no_verify":
        command.append("--no-verify")
    command_text = f"VERUS_Z3_PATH={z3} " + " ".join(command)
    progress = run_dir / "progress.jsonl"
    append_jsonl(
        progress,
        {
            "ts": now(),
            "event": "trial_started",
            "run_id": run_id,
            "done": done_before,
            "total": 2,
            "phase": mode,
            "protocol": "float_model_boundary",
            "task_id": name,
            "status": "running",
            "message": command_text,
        },
    )
    started = time.monotonic()
    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(z3)
    completed = subprocess.run(
        command,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    trial_dir = run_dir / "trials" / name
    atomic_bytes(trial_dir / "stdout.log", completed.stdout)
    atomic_bytes(trial_dir / "stderr.log", completed.stderr)
    atomic_bytes(trial_dir / "command.txt", (command_text + "\n").encode())
    atomic_bytes(
        trial_dir / "rc.txt",
        f"{completed.returncode}\n".encode(),
    )
    output = (completed.stdout + completed.stderr).decode(
        errors="replace"
    )
    passed = completed.returncode != 0 and expected_fragment in output
    result = {
        "schema_version": 1,
        "run_id": run_id,
        "trial": name,
        "status": "passed" if passed else "failed",
        "expected_rejection": True,
        "expected_fragment": expected_fragment,
        "expected_fragment_observed": expected_fragment in output,
        "exit_code": completed.returncode,
        "mode": mode,
        "command": command,
        "command_text": command_text,
        "source_path": str(source.relative_to(ROOT)),
        "source_sha256": sha256(source),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
        "duration_seconds": time.monotonic() - started,
        "stdout_path": str((trial_dir / "stdout.log").relative_to(ROOT)),
        "stdout_sha256": sha256(trial_dir / "stdout.log"),
        "stderr_path": str((trial_dir / "stderr.log").relative_to(ROOT)),
        "stderr_sha256": sha256(trial_dir / "stderr.log"),
    }
    atomic_json(trial_dir / "result.json", result)
    append_jsonl(run_dir / "run_results.jsonl", result)
    append_jsonl(
        progress,
        {
            "ts": now(),
            "event": "trial_done" if passed else "trial_failed",
            "run_id": run_id,
            "done": done_before + 1,
            "total": 2,
            "phase": mode,
            "protocol": "float_model_boundary",
            "task_id": name,
            "status": result["status"],
            "message": (
                "expected verifier rejection observed"
                if passed
                else "expected verifier rejection was not observed"
            ),
        },
    )
    return {
        **result,
        "result_path": str((trial_dir / "result.json").relative_to(ROOT)),
        "result_sha256": sha256(trial_dir / "result.json"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    parser.add_argument("--z3", type=Path, default=DEFAULT_Z3)
    args = parser.parse_args()
    if not valid_run_id(args.run_id):
        raise SystemExit("invalid run id")
    if args.timeout < 1:
        raise SystemExit("timeout must be positive")
    verus = args.verus.resolve()
    z3 = args.z3.resolve()
    for path in (verus, z3, SEMANTICS_PROBE, OVERRIDE_PROBE):
        if not path.is_file():
            raise FileNotFoundError(path)
    run_dir = EVIDENCE_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    progress = run_dir / "progress.jsonl"
    progress.touch()
    (run_dir / "run_results.jsonl").touch()
    (run_dir / "stdout.log").touch()
    (run_dir / "stderr.log").touch()
    atomic_bytes(run_dir / "pid", f"{os.getpid()}\n".encode())
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "objective": (
            "Test whether loaded vstd float predicates prove Rust 1.96 "
            "comparison functionality/NaN semantics or permit a stronger "
            "local target binding."
        ),
        "expected_trials": 2,
        "budget": {
            "maximum_commands": 2,
            "timeout_seconds_per_command": args.timeout,
        },
        "model_routes": ["local_verus"],
        "commands": [
            "actual Verus over research/float_model_semantics_probe.rs",
            "Verus --no-verify over research/float_stronger_contract_probe.rs",
        ],
        "source_snapshot": [
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256(path),
            }
            for path in (SEMANTICS_PROBE, OVERRIDE_PROBE)
        ],
        "verus_path": str(verus),
        "verus_binary_sha256": sha256(verus),
        "z3_path": str(z3),
        "z3_sha256": sha256(z3),
    }
    atomic_json(run_dir / "manifest.json", manifest)
    status = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "running",
        "done": 0,
        "total": 2,
        "current_item": "float_semantics_unavailable",
        "started_at": now(),
        "updated_at": now(),
    }
    atomic_json(run_dir / "status.json", status)
    append_jsonl(
        progress,
        {
            "ts": now(),
            "event": "run_started",
            "run_id": args.run_id,
            "done": 0,
            "total": 2,
            "phase": "model_probe",
            "protocol": "float_model_boundary",
            "task_id": "",
            "status": "running",
            "message": manifest["objective"],
        },
    )
    trials = []
    trial_specs = (
        (
            "float_semantics_unavailable",
            SEMANTICS_PROBE,
            "actual",
            "postcondition not satisfied",
        ),
        (
            "stronger_contract_rejected",
            OVERRIDE_PROBE,
            "no_verify",
            "duplicate specification",
        ),
    )
    for index, (name, source, mode, fragment) in enumerate(
        trial_specs, start=1
    ):
        if (run_dir / "STOP").exists():
            append_jsonl(
                progress,
                {
                    "ts": now(),
                    "event": "run_cancelled",
                    "run_id": args.run_id,
                    "done": index - 1,
                    "total": 2,
                    "phase": "model_probe",
                    "protocol": "float_model_boundary",
                    "task_id": name,
                    "status": "cancelled",
                    "message": "run-scoped STOP requested",
                },
            )
            status.update(
                status="cancelled",
                done=index - 1,
                current_item=name,
                updated_at=now(),
            )
            atomic_json(run_dir / "status.json", status)
            return 130
        result = run_trial(
            run_id=args.run_id,
            run_dir=run_dir,
            name=name,
            source=source,
            mode=mode,
            expected_fragment=fragment,
            done_before=index - 1,
            verus=verus,
            z3=z3,
            timeout=args.timeout,
        )
        trials.append(result)
        status.update(
            done=index,
            current_item=name,
            updated_at=now(),
        )
        atomic_json(run_dir / "status.json", status)
    passed = all(trial["status"] == "passed" for trial in trials)
    result = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "passed" if passed else "failed",
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "trial_count": len(trials),
        "passed_trial_count": sum(
            trial["status"] == "passed" for trial in trials
        ),
        "trials": [
            {
                "name": trial["trial"],
                "path": trial["result_path"],
                "sha256": trial["result_sha256"],
            }
            for trial in trials
        ],
    }
    atomic_json(run_dir / "result.json", result)
    status.update(
        status=result["status"],
        done=len(trials),
        current_item="",
        updated_at=now(),
        completed_at=now(),
    )
    atomic_json(run_dir / "status.json", status)
    append_jsonl(
        progress,
        {
            "ts": now(),
            "event": "run_completed" if passed else "run_failed",
            "run_id": args.run_id,
            "done": len(trials),
            "total": 2,
            "phase": "model_probe",
            "protocol": "float_model_boundary",
            "task_id": "",
            "status": result["status"],
            "message": "all expected model-boundary rejections observed",
        },
    )
    latest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": result["status"],
        "run_dir": str(run_dir.relative_to(ROOT)),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "result_sha256": sha256(run_dir / "result.json"),
    }
    atomic_json(EVIDENCE_ROOT / "latest.json", latest)
    output = json.dumps(result, sort_keys=True)
    atomic_bytes(run_dir / "stdout.log", (output + "\n").encode())
    print(output)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
