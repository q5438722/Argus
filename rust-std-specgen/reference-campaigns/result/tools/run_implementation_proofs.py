#!/usr/bin/env python3
"""Protocol-compliant runner for the core::result implementation-conformance gate.

Every target contributes exactly eight commands:

    implementation_proof.rs                 --no-verify   expect rc == 0
    implementation_proof.rs                 actual        expect rc == 0
    completeness_proof.rs                   --no-verify   expect rc == 0
    completeness_proof.rs                   actual        expect rc == 0
    mutations/implementation_mutant.rs      --no-verify   expect rc == 0
    mutations/implementation_mutant.rs      actual        expect rc != 0
    mutations/completeness_mutant.rs        --no-verify   expect rc == 0
    mutations/completeness_mutant.rs        actual        expect rc != 0

The run directory follows `docs/LIVE_EXPERIMENT_PROTOCOL.md`: an immutable
`manifest.json`, an atomically replaced `status.json`, an fsync'ed append-only
`progress.jsonl`, a run-scoped `STOP` flag checked before every command, and
complete per-command stdout/stderr/rc capture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
Z3 = ROOT.parent / "verus/source/z3"
HARNESS_ROOT = ROOT / "proof_harnesses"
SCHEMA = 2
VERIFICATION_RE = re.compile(
    r"verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors"
)

COMMANDS = (
    ("implementation_no_verify", "implementation_proof.rs", True, "accepted"),
    ("implementation_actual", "implementation_proof.rs", False, "accepted"),
    ("completeness_no_verify", "completeness_proof.rs", True, "accepted"),
    ("completeness_actual", "completeness_proof.rs", False, "accepted"),
    ("implementation_mutant_no_verify", "mutations/implementation_mutant.rs", True, "accepted"),
    ("implementation_mutant_actual", "mutations/implementation_mutant.rs", False, "rejected"),
    ("completeness_mutant_no_verify", "mutations/completeness_mutant.rs", True, "accepted"),
    ("completeness_mutant_actual", "mutations/completeness_mutant.rs", False, "rejected"),
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def atomic_write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


class RunDirectory:
    """Durable, interruptible run directory per the live-experiment protocol."""

    def __init__(self, run_dir: Path, run_id: str) -> None:
        self.path = run_dir
        self.run_id = run_id
        self.path.mkdir(parents=True, exist_ok=True)
        self.progress_path = self.path / "progress.jsonl"
        self.status_path = self.path / "status.json"
        self.manifest_path = self.path / "manifest.json"
        self.results_path = self.path / "results.jsonl"
        self.stop_path = self.path / "STOP"

    def stop_requested(self) -> bool:
        return self.stop_path.exists()

    def write_manifest(self, payload: dict[str, Any]) -> None:
        if self.manifest_path.exists():
            existing = json.loads(self.manifest_path.read_text())
            raise SystemExit(
                f"run directory {self.path} already holds an immutable manifest "
                f"for run {existing.get('run_id')!r}; use a fresh run id/directory"
            )
        atomic_write_json(self.manifest_path, payload)

    def event(self, kind: str, **fields: Any) -> None:
        record = {"run_id": self.run_id, "timestamp_utc": utc_now(), "event": kind, **fields}
        with self.progress_path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def result_row(self, record: dict[str, Any]) -> None:
        with self.results_path.open("a") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
            handle.flush()
            os.fsync(handle.fileno())

    def status(self, payload: dict[str, Any]) -> None:
        atomic_write_json(self.status_path, {"run_id": self.run_id, **payload})


def tool_identity() -> dict[str, Any]:
    def capture(command: list[str]) -> str:
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
            return (completed.stdout or completed.stderr).strip()
        except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover
            return f"unavailable: {exc}"

    rustc = os.environ.get("RUSTC", "rustc")
    return {
        "verus_binary": str(VERUS),
        "verus_binary_sha256": sha256_file(VERUS),
        "verus_version": capture([str(VERUS), "--version"]),
        "z3_binary": str(Z3),
        "z3_binary_sha256": sha256_file(Z3),
        "z3_version": capture([str(Z3), "--version"]),
        "rustc_command": [rustc, "+1.96.0", "--version", "--verbose"],
        "rustc_version": capture([rustc, "+1.96.0", "--version", "--verbose"]),
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
    }


def target_directories(only: str | None) -> list[Path]:
    directories = sorted(path for path in HARNESS_ROOT.iterdir() if path.is_dir())
    if only:
        wanted = {name.strip() for name in only.split(",") if name.strip()}
        directories = [path for path in directories if path.name in wanted]
        missing = wanted - {path.name for path in directories}
        if missing:
            raise SystemExit(f"unknown target directories: {sorted(missing)}")
    return directories


def proof_closure_paths(target: Path) -> dict[str, Path]:
    proof_manifest = ROOT / "proof_manifests" / target.name
    return {
        "implementation_proof.rs": target / "implementation_proof.rs",
        "completeness_proof.rs": target / "completeness_proof.rs",
        "mutations/implementation_mutant.rs": (
            target / "mutations/implementation_mutant.rs"
        ),
        "mutations/completeness_mutant.rs": (
            target / "mutations/completeness_mutant.rs"
        ),
        "accepted_contract.rs": target / "accepted_contract.rs",
        "source_excerpt.rs": target / "source_excerpt.rs",
        "contract_equivalence.json": target / "contract_equivalence.json",
        "transformation_manifest.json": target / "transformation_manifest.json",
        "dependency_assumptions.json": target / "dependency_assumptions.json",
        "trust_boundaries.json": target / "trust_boundaries.json",
        "manifest.json": target / "manifest.json",
        "proof_manifests/source_body.json": proof_manifest / "source_body.json",
        "proof_manifests/transformation_manifest.json": (
            proof_manifest / "transformation_manifest.json"
        ),
        "proof_manifests/dependency_assumption_manifest.json": (
            proof_manifest / "dependency_assumption_manifest.json"
        ),
        "proof_manifests/proof_manifest.json": (
            proof_manifest / "proof_manifest.json"
        ),
        "frozen_inputs/source_dependency_manifest.json": (
            ROOT / "frozen_inputs/source_dependency_manifest.json"
        ),
        "specs/result_shared_vocabulary.rs": (
            ROOT / "specs/result_shared_vocabulary.rs"
        ),
        "specs/all_result_specs.json": ROOT / "specs/all_result_specs.json",
        "implementation.py": ROOT / "implementation.py",
        "proofgen/families.py": ROOT / "proofgen/families.py",
        "proofgen/model.py": ROOT / "proofgen/model.py",
        "proofgen/render.py": ROOT / "proofgen/render.py",
        "tools/run_implementation_proofs.py": Path(__file__).resolve(),
        "tools/check_implementation_proofs.py": (
            ROOT / "tools/check_implementation_proofs.py"
        ),
    }


def run_command(
    run: RunDirectory,
    target: Path,
    name: str,
    relative_input: str,
    no_verify: bool,
    expectation: str,
    timeout: int,
    tools: dict[str, Any],
) -> dict[str, Any]:
    input_path = target / relative_input
    relative = input_path.relative_to(ROOT)
    argv = [str(VERUS), "--crate-type=lib", "--triggers-mode", "silent"]
    if no_verify:
        argv.append("--no-verify")
    argv.append(str(relative))

    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(Z3)

    command_text = (
        f"VERUS_Z3_PATH={Z3} {VERUS} --crate-type=lib --triggers-mode silent"
        + (" --no-verify" if no_verify else "")
        + f" {relative}"
    )

    evidence = target / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)

    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            argv,
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=timeout,
        )
        stdout, stderr, return_code = completed.stdout, completed.stderr, completed.returncode
    except subprocess.TimeoutExpired as expired:
        timed_out = True
        stdout = expired.stdout.decode() if isinstance(expired.stdout, bytes) else (expired.stdout or "")
        stderr = expired.stderr.decode() if isinstance(expired.stderr, bytes) else (expired.stderr or "")
        return_code = 124
    duration_ms = int((time.monotonic() - started) * 1000)

    write_text(evidence / f"{name}.command.txt", command_text + "\n")
    write_text(evidence / f"{name}.stdout.txt", stdout)
    write_text(evidence / f"{name}.stderr.txt", stderr)
    write_text(evidence / f"{name}.rc.txt", f"{return_code}\n")

    combined_output = stdout + "\n" + stderr
    verification_match = VERIFICATION_RE.search(combined_output)
    parsed_verification = (
        {
            "verified": int(verification_match.group(1)),
            "errors": int(verification_match.group(2)),
        }
        if verification_match
        else {"verified": None, "errors": None}
    )
    verification_failure = (
        parsed_verification["errors"] not in (None, 0)
        or "postcondition not satisfied" in stderr
        or "precondition not satisfied" in stderr
        or "assertion failed" in stderr
    )
    if expectation == "accepted":
        expectation_met = return_code == 0
        if not no_verify:
            expectation_met = (
                expectation_met
                and isinstance(parsed_verification["verified"], int)
                and parsed_verification["verified"] > 0
                and parsed_verification["errors"] == 0
            )
    else:
        expectation_met = return_code != 0 and verification_failure
    if timed_out:
        expectation_met = False

    record = {
        "schema_version": SCHEMA,
        "run_id": run.run_id,
        "run_dir": str(run.path),
        "name": name,
        "target_directory": target.name,
        "completed_at_utc": utc_now(),
        "argv": argv,
        "command_text": command_text,
        "environment": {"VERUS_Z3_PATH": str(Z3)},
        "input_path": str(relative),
        "input_sha256": sha256_file(input_path),
        "proof_closure_sha256": {
            relative: sha256_file(path)
            for relative, path in proof_closure_paths(target).items()
        },
        "no_verify": no_verify,
        "expected": expectation,
        "return_code": return_code,
        "timed_out": timed_out,
        "parsed_verification": parsed_verification,
        "verification_failure": verification_failure,
        "timeout_seconds": timeout,
        "duration_ms": duration_ms,
        "stdout_path": f"evidence/{name}.stdout.txt",
        "stderr_path": f"evidence/{name}.stderr.txt",
        "stdout_sha256": sha256_bytes(stdout.encode()),
        "stderr_sha256": sha256_bytes(stderr.encode()),
        "command_sha256": sha256_file(evidence / f"{name}.command.txt"),
        "rc_sha256": sha256_file(evidence / f"{name}.rc.txt"),
        "tools": tools,
        "expectation_met": expectation_met,
        "success": expectation_met,
    }
    atomic_write_json(evidence / f"{name}.json", record)
    return record


def summarize(run: RunDirectory, records: list[dict[str, Any]], full_batch: bool) -> dict[str, Any]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_target.setdefault(record["target_directory"], []).append(record)
    complete = [name for name, rows in by_target.items() if len(rows) == len(COMMANDS)]
    expectations_met = all(record["expectation_met"] for record in records)
    summary = {
        "schema_version": SCHEMA,
        "run_id": run.run_id,
        "run_dir": str(run.path),
        "generated_at_utc": utc_now(),
        "mode": "full_batch" if full_batch else "selected_targets",
        "targets_attempted": len(by_target),
        "targets_with_complete_matrices": len(complete),
        "commands_recorded": len(records),
        "commands_expected_for_full_batch": 64 * len(COMMANDS),
        "successful_expectations": sum(bool(r["expectation_met"]) for r in records),
        "failed_expectations": [
            {"target": r["target_directory"], "name": r["name"], "return_code": r["return_code"]}
            for r in records
            if not r["expectation_met"]
        ],
        "all_recorded_expectations_met": expectations_met,
        "full_64_target_batch_run": full_batch and len(complete) == 64,
        "evidence_current": bool(
            expectations_met and full_batch and len(complete) == 64 and len(records) == 512
        ),
        "records": [
            {
                "target": r["target_directory"],
                "name": r["name"],
                "return_code": r["return_code"],
                "duration_ms": r["duration_ms"],
                "expectation_met": r["expectation_met"],
                "input_sha256": r["input_sha256"],
            }
            for r in records
        ],
    }
    atomic_write_json(run.path / "summary.json", summary)
    atomic_write_json(ROOT / "verification/live_runs" / f"{run.run_id}.summary.json", summary)
    atomic_write_json(ROOT / "verification/representative_diagnostics.json", summary)
    return summary


def write_full_run_binding(
    run: RunDirectory,
    summary: dict[str, Any],
    tools: dict[str, Any],
) -> None:
    if not summary["evidence_current"]:
        return
    artifacts = {}
    for label, path in (
        ("manifest", run.manifest_path),
        ("status", run.status_path),
        ("progress", run.progress_path),
        ("results", run.results_path),
        ("summary", run.path / "summary.json"),
    ):
        artifacts[label] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": sha256_file(path),
            "size": path.stat().st_size,
        }
    atomic_write_json(
        ROOT / "proof_inventory/verification_run.json",
        {
            "schema_version": SCHEMA,
            "run_id": run.run_id,
            "run_dir": str(run.path.relative_to(ROOT)),
            "state": "completed",
            "target_count": 64,
            "commands_per_target": len(COMMANDS),
            "commands_recorded": summary["commands_recorded"],
            "mutation_rejections": 128,
            "evidence_current": True,
            "proof_inventory_sha256": sha256_file(
                ROOT / "proof_inventory/targets.json"
            ),
            "tools": tools,
            "artifacts": artifacts,
            "bound_at_utc": utc_now(),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True, help="stable identifier for this run")
    parser.add_argument("--run-dir", required=True, help="durable run directory")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true", help="run all 64 targets (512 commands)")
    group.add_argument("--targets", help="comma-separated target directory names")
    parser.add_argument("--timeout", type=int, default=300, help="per-command timeout in seconds")
    parser.add_argument("--clear-stop", action="store_true", help="clear a stale STOP flag")
    args = parser.parse_args()

    if not VERUS.is_file() or not Z3.is_file():
        raise SystemExit("verus and z3 binaries are required")

    run = RunDirectory(Path(args.run_dir).resolve(), args.run_id)
    if run.stop_requested():
        if not args.clear_stop:
            raise SystemExit(f"stale STOP flag in {run.path}; pass --clear-stop to override")
        run.stop_path.unlink()

    targets = target_directories(args.targets)
    tools = tool_identity()
    run.write_manifest(
        {
            "schema_version": SCHEMA,
            "run_id": args.run_id,
            "created_at_utc": utc_now(),
            "objective": (
                "Run the eight-command implementation/completeness/mutation matrix for "
                "each selected core::result target and record complete, hash-bound "
                "evidence."
            ),
            "project_root": str(ROOT),
            "command": " ".join(sys.argv),
            "targets": [path.name for path in targets],
            "target_count": len(targets),
            "commands_per_target": len(COMMANDS),
            "expected_commands": len(targets) * len(COMMANDS),
            "full_batch": bool(args.all),
            "timeout_seconds": args.timeout,
            "tools": tools,
            "inputs": {
                "proof_inventory": sha256_file(ROOT / "proof_inventory/targets.json"),
                "accepted_catalog": sha256_file(ROOT / "specs/all_result_specs.json"),
                "accepted_manifest": sha256_file(
                    ROOT / "specs/specification_package_manifest.json"
                ),
                "proof_stage_authorization": sha256_file(
                    ROOT / "proof_stage/authorization.json"
                ),
                "source_dependency_manifest": sha256_file(
                    ROOT / "frozen_inputs/source_dependency_manifest.json"
                ),
                "implementation_generator": sha256_file(ROOT / "implementation.py"),
                "family_templates": sha256_file(ROOT / "proofgen/families.py"),
                "proof_model": sha256_file(ROOT / "proofgen/model.py"),
                "proof_renderer": sha256_file(ROOT / "proofgen/render.py"),
                "runner": sha256_file(Path(__file__).resolve()),
                "checker": sha256_file(
                    ROOT / "tools/check_implementation_proofs.py"
                ),
            },
        }
    )
    run.event("run_started", targets=len(targets), commands=len(targets) * len(COMMANDS))
    run.status(
        {
            "state": "running",
            "updated_at_utc": utc_now(),
            "targets_total": len(targets),
            "targets_done": 0,
            "commands_done": 0,
            "commands_total": len(targets) * len(COMMANDS),
            "failed_expectations": 0,
        }
    )

    records: list[dict[str, Any]] = []
    cancelled = False
    for index, target in enumerate(targets, 1):
        if run.stop_requested():
            cancelled = True
            break
        run.event("trial_started", target=target.name, index=index)
        for name, relative_input, no_verify, expectation in COMMANDS:
            if run.stop_requested():
                cancelled = True
                break
            record = run_command(
                run, target, name, relative_input, no_verify, expectation, args.timeout, tools
            )
            records.append(record)
            run.result_row(
                {
                    "target": target.name,
                    "name": name,
                    "return_code": record["return_code"],
                    "expectation_met": record["expectation_met"],
                    "duration_ms": record["duration_ms"],
                }
            )
            run.status(
                {
                    "state": "running",
                    "updated_at_utc": utc_now(),
                    "targets_total": len(targets),
                    "targets_done": index - 1,
                    "current_target": target.name,
                    "current_command": name,
                    "commands_done": len(records),
                    "commands_total": len(targets) * len(COMMANDS),
                    "failed_expectations": sum(
                        1 for entry in records if not entry["expectation_met"]
                    ),
                }
            )
        if cancelled:
            run.event("run_cancelled", target=target.name)
            break
        run.event(
            "trial_done",
            target=target.name,
            index=index,
            failures=sum(
                1
                for entry in records
                if entry["target_directory"] == target.name and not entry["expectation_met"]
            ),
        )

    summary = summarize(run, records, bool(args.all) and not cancelled)
    state = "cancelled" if cancelled else ("completed" if summary["all_recorded_expectations_met"] else "failed")
    run.status(
        {
            "state": state,
            "updated_at_utc": utc_now(),
            "targets_total": len(targets),
            "commands_done": len(records),
            "commands_total": len(targets) * len(COMMANDS),
            "all_recorded_expectations_met": summary["all_recorded_expectations_met"],
            "evidence_current": summary["evidence_current"],
            "summary_path": str(run.path / "summary.json"),
        }
    )
    run.event(
        "run_cancelled" if cancelled else ("run_completed" if summary["all_recorded_expectations_met"] else "run_failed"),
        commands=len(records),
        failures=len(summary["failed_expectations"]),
    )
    write_full_run_binding(run, summary, tools)
    print(json.dumps({k: v for k, v in summary.items() if k != "records"}, indent=2, sort_keys=True))
    if cancelled:
        return 130
    return 0 if summary["all_recorded_expectations_met"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
