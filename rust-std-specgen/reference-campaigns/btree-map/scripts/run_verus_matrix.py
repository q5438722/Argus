#!/usr/bin/env python3
"""Run the complete BTreeMap Verus and mutation matrix with live evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_campaign


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "inventory/btree_map_exec_fn_inventory.json"
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
Z3 = ROOT.parent / "verus/source/target-verus/release/z3"
EVIDENCE_ROOT = ROOT / "verification/evidence/verus_matrix"
POSITIVE_RESULT = re.compile(r"verification results::\s+\d+ verified, 0 errors")
MUTATION_RESULT = re.compile(
    r"verification results::\s+\d+ verified, ([1-9]\d*) errors"
)
ERROR_BLOCK = re.compile(
    r"^error: (?P<kind>[^\n]+)\n(?P<body>.*?)(?=^error: |\Z)",
    re.MULTILINE | re.DOTALL,
)
ERROR_LOCATION = re.compile(r"^\s*-->\s+.*:(\d+):\d+\s*$", re.MULTILINE)


def mutation_function_line_ranges(source: str) -> dict[str, tuple[int, int]]:
    matches = list(
        re.finditer(
            r"^pub\s+(?:proof\s+)?fn\s+(mutation_[A-Za-z0-9_]+)\b",
            source,
            re.MULTILINE,
        )
    )
    total_lines = source.count("\n") + 1
    ranges: dict[str, tuple[int, int]] = {}
    for index, match in enumerate(matches):
        start = source.count("\n", 0, match.start()) + 1
        end = (
            source.count("\n", 0, matches[index + 1].start())
            if index + 1 < len(matches)
            else total_lines
        )
        ranges[match.group(1)] = (start, end)
    return ranges


def analyze_mutation_diagnostics(
    source: str,
    combined_output: str,
    expected_functions: list[str],
) -> dict[str, Any]:
    ranges = mutation_function_line_ranges(source)
    diagnostics: list[dict[str, Any]] = []
    for match in ERROR_BLOCK.finditer(combined_output):
        kind = match.group("kind").strip()
        if kind.startswith("aborting due to"):
            continue
        location = ERROR_LOCATION.search(match.group("body"))
        line = int(location.group(1)) if location is not None else None
        function = next(
            (
                name
                for name, (start, end) in ranges.items()
                if line is not None and start <= line <= end
            ),
            None,
        )
        diagnostics.append(
            {"kind": kind, "line": line, "function": function}
        )
    rejected_functions = [
        diagnostic["function"]
        for diagnostic in diagnostics
        if diagnostic["kind"] == "postcondition not satisfied"
        and diagnostic["function"] is not None
    ]
    return {
        "diagnostics": diagnostics,
        "rejected_functions": rejected_functions,
        "passed": (
            len(diagnostics) == len(expected_functions)
            and all(
                diagnostic["kind"] == "postcondition not satisfied"
                for diagnostic in diagnostics
            )
            and sorted(rejected_functions) == sorted(expected_functions)
            and len(rejected_functions) == len(set(rejected_functions))
        ),
    }


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


class LiveRun:
    def __init__(self, run_id: str, total: int, manifest: dict[str, Any]) -> None:
        self.run_id = run_id
        self.root = EVIDENCE_ROOT / run_id
        if self.root.exists():
            raise RuntimeError(f"run directory already exists: {self.root}")
        self.root.mkdir(parents=True)
        self.total = total
        self.done = 0
        self.failed = 0
        self.started = now()
        atomic_json(self.root / "manifest.json", manifest)
        for name in ("progress.jsonl", "run_results.jsonl", "stdout.log", "stderr.log"):
            (self.root / name).touch()
        (self.root / "pid").write_text(f"{os.getpid()}\n")
        self.status("pending", current=None)

    def append_jsonl(self, name: str, value: dict[str, Any]) -> None:
        with (self.root / name).open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(value, sort_keys=True) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

    def status(self, state: str, current: str | None) -> None:
        atomic_json(
            self.root / "status.json",
            {
                "schema_version": 1,
                "run_id": self.run_id,
                "status": state,
                "done": self.done,
                "failed": self.failed,
                "total": self.total,
                "current": current,
                "started_at": self.started,
                "updated_at": now(),
            },
        )

    def event(self, event: str, **extra: Any) -> None:
        payload = {
            "ts": now(),
            "event": event,
            "run_id": self.run_id,
            "done": self.done,
            "total": self.total,
            "phase": "verus_matrix",
            "protocol": "rust_std_btree_map",
            **extra,
        }
        self.append_jsonl("progress.jsonl", payload)
        print(json.dumps(payload, sort_keys=True), flush=True)

    def log(self, stdout: str, stderr: str, label: str) -> None:
        for filename, content in (("stdout.log", stdout), ("stderr.log", stderr)):
            with (self.root / filename).open("a", encoding="utf-8") as stream:
                stream.write(f"\n===== {label} =====\n")
                stream.write(content)
                if content and not content.endswith("\n"):
                    stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())

    def cancelled(self) -> bool:
        return (self.root / "STOP").exists()


def command_for(path: Path, no_verify: bool) -> list[str]:
    command = [
        str(VERUS),
        "--crate-type=lib",
        "--triggers-mode",
        "silent",
    ]
    if no_verify:
        command.append("--no-verify")
    command.append(str(path))
    return command


def write_evidence(
    evidence_root: Path,
    name: str,
    command: list[str],
    source: Path,
    result: subprocess.CompletedProcess[str],
    duration_ms: int,
    passed: bool,
    expectation: str,
) -> dict[str, Any]:
    rendered = shlex.join(command)
    (evidence_root / f"{name}.command").write_text(rendered + "\n")
    (evidence_root / f"{name}.stdout").write_text(result.stdout)
    (evidence_root / f"{name}.stderr").write_text(result.stderr)
    (evidence_root / f"{name}.rc").write_text(f"{result.returncode}\n")
    record = {
        "schema_version": 1,
        "name": name,
        "command": command,
        "cwd": str(ROOT),
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256_file(source),
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "expectation": expectation,
        "passed": passed,
        "completed_at": now(),
    }
    atomic_json(evidence_root / f"{name}.json", record)
    return record


def execute_trial(
    live: LiveRun,
    target_id: str,
    trial_name: str,
    path: Path,
    no_verify: bool,
    expected_mutation_functions: list[str] | None = None,
    evidence_root_override: Path | None = None,
) -> dict[str, Any]:
    command = command_for(path, no_verify)
    live.event(
        "trial_started",
        task_id=target_id,
        trial=trial_name,
        status="running",
        message=shlex.join(command),
    )
    live.status("running", f"{target_id}/{trial_name}")
    started = time.monotonic()
    try:
        result = subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
        duration_ms = int((time.monotonic() - started) * 1000)
    except subprocess.TimeoutExpired as error:
        duration_ms = int((time.monotonic() - started) * 1000)
        result = subprocess.CompletedProcess(
            command,
            124,
            error.stdout or "",
            (error.stderr or "") + "\nTIMEOUT\n",
        )

    combined = result.stdout + "\n" + result.stderr
    rejected_mutation_functions = 0
    rejected_mutation_function_names: list[str] = []
    mutation_diagnostics: list[dict[str, Any]] = []
    if expected_mutation_functions is not None:
        expected_mutation_count = len(expected_mutation_functions)
        mutation_match = MUTATION_RESULT.search(combined)
        result_error_count = (
            int(mutation_match.group(1)) if mutation_match is not None else 0
        )
        diagnostic_analysis = analyze_mutation_diagnostics(
            path.read_text(),
            combined,
            expected_mutation_functions,
        )
        rejected_mutation_function_names = diagnostic_analysis[
            "rejected_functions"
        ]
        rejected_mutation_functions = len(rejected_mutation_function_names)
        mutation_diagnostics = diagnostic_analysis["diagnostics"]
        passed = (
            result.returncode != 0
            and result_error_count == expected_mutation_count
            and diagnostic_analysis["passed"]
        )
        expectation = (
            "actual Verus attributes exactly one postcondition failure to every "
            "manifested source-shaped mutation and no other diagnostic"
        )
    elif no_verify:
        passed = result.returncode == 0
        expectation = "Verus --no-verify accepts exact harness syntax and types"
    else:
        passed = result.returncode == 0 and POSITIVE_RESULT.search(combined) is not None
        expectation = "actual Verus reports verified with zero errors"

    evidence_root = evidence_root_override or (path.parent / "evidence")
    evidence_root.mkdir(exist_ok=True)
    record = write_evidence(
        evidence_root,
        trial_name,
        command,
        path,
        result,
        duration_ms,
        passed,
        expectation,
    )
    record["rejected_mutation_functions"] = rejected_mutation_functions
    record["rejected_mutation_function_names"] = (
        rejected_mutation_function_names
    )
    record["expected_mutation_functions"] = (
        len(expected_mutation_functions)
        if expected_mutation_functions is not None
        else 0
    )
    record["expected_mutation_function_names"] = (
        expected_mutation_functions or []
    )
    record["mutation_diagnostics"] = mutation_diagnostics
    atomic_json(evidence_root / f"{trial_name}.json", record)
    live.log(result.stdout, result.stderr, f"{target_id}/{trial_name}")
    live.done += 1
    if not passed:
        live.failed += 1
    record.update({"target_id": target_id, "trial": trial_name})
    live.append_jsonl("run_results.jsonl", record)
    live.event(
        "trial_done" if passed else "trial_failed",
        task_id=target_id,
        trial=trial_name,
        status="passed" if passed else "failed",
        message=f"rc={result.returncode} duration_ms={duration_ms}",
    )
    return record


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = json.loads(INVENTORY.read_text())
    rows = [
        row
        for row in inventory["rows"]
        if row["disposition"] in {"exact_vstd", "generated"}
    ]
    phase_path = ROOT / "verification/premature_phase_ordering.json"
    phase = json.loads(phase_path.read_text())
    if phase.get("accepted_as_proof_evidence"):
        for key in (
            "verus_matrix_manifest",
            "verus_matrix_manifest_sha256",
            "verus_matrix_run_id",
            "verus_matrix_summary",
            "verus_matrix_summary_sha256",
        ):
            phase.pop(key, None)
        phase.update(
            {
                "status": "post_authorization_generation_recorded",
                "accepted_as_proof_evidence": False,
                "proof_status": "generated_pending_fresh_dynamic_evidence",
                "next_legal_transition": (
                    "complete this fresh post-authorization Verus matrix and "
                    "bind it during campaign finalization"
                ),
            }
        )
        atomic_json(phase_path, phase)
    generated_file_count, generated_tree_sha256 = (
        generate_campaign.generated_harness_tree_digest(rows)
    )
    if (
        phase.get("file_count") != generated_file_count
        or phase.get("tree_sha256") != generated_tree_sha256
        or not phase.get("proof_phase_authorized")
    ):
        raise RuntimeError(
            "phase-order archive does not bind the generated proof tree"
        )
    total = 1 + len(rows) * 5
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "objective": (
            "Run generated-spec no-verify plus implementation/completeness "
            "no-verify, actual Verus, and negative mutation for every selected API"
        ),
        "command": [sys.executable, "scripts/run_verus_matrix.py", "--run-id", args.run_id],
        "expected_trials": total,
        "model_routes": [],
        "budget": {"max_trials": total, "per_trial_timeout_seconds": 90},
        "source_snapshot": {
            "inventory": str(INVENTORY.relative_to(ROOT)),
            "inventory_sha256": sha256_file(INVENTORY),
            "phase_order_archive": str(phase_path.relative_to(ROOT)),
            "phase_order_archive_sha256": sha256_file(phase_path),
            "generated_harness_file_count": generated_file_count,
            "generated_harness_tree_sha256": generated_tree_sha256,
            "verus": str(VERUS),
            "verus_sha256": sha256_file(VERUS),
            "z3": str(Z3),
            "z3_sha256": sha256_file(Z3),
        },
        "created_at": now(),
    }
    live = LiveRun(args.run_id, total, manifest)
    live.status("running", "generated_spec_no_verify")
    live.event("run_started", status="running", message=f"{len(rows)} targets")

    versions = {
        "verus": subprocess.check_output([str(VERUS), "--version"], text=True).splitlines(),
        "z3": subprocess.check_output([str(Z3), "-version"], text=True).splitlines(),
    }
    spec_path = ROOT / "specs/generated_btree_map_specs.rs"
    spec_record = execute_trial(
        live,
        "module_spec",
        "generated_spec_no_verify",
        spec_path,
        True,
        evidence_root_override=live.root / "module_spec_evidence",
    )

    target_summaries: list[dict[str, Any]] = []
    cancelled = False
    for row in rows:
        if live.cancelled():
            cancelled = True
            live.event(
                "run_cancelled",
                task_id=row["target_id"],
                status="cancelled",
                message="STOP file observed",
            )
            break
        target_id = row["target_id"]
        target_root = ROOT / "proof_harnesses" / target_id
        evidence_root = target_root / "evidence"
        mutation_manifest = json.loads(
            (target_root / "mutations.json").read_text()
        )
        expected_mutation_functions = [
            mutant["function"] for mutant in mutation_manifest["mutants"]
        ]
        if not expected_mutation_functions:
            raise RuntimeError(f"{target_id}: empty mutation manifest")
        atomic_json(evidence_root / "versions.json", versions)
        trials = [
            execute_trial(
                live,
                target_id,
                "implementation_no_verify",
                target_root / "implementation_proof.rs",
                True,
            ),
            execute_trial(
                live,
                target_id,
                "implementation_actual_verus",
                target_root / "implementation_proof.rs",
                False,
            ),
            execute_trial(
                live,
                target_id,
                "completeness_no_verify",
                target_root / "completeness_proof.rs",
                True,
            ),
            execute_trial(
                live,
                target_id,
                "completeness_actual_verus",
                target_root / "completeness_proof.rs",
                False,
            ),
            execute_trial(
                live,
                target_id,
                "mutation_actual_verus",
                target_root / "mutation_proof.rs",
                False,
                expected_mutation_functions=expected_mutation_functions,
            ),
        ]
        target_summaries.append(
            {
                "target_id": target_id,
                "passed": all(trial["passed"] for trial in trials),
                "trials": {
                    trial["trial"]: {
                        "passed": trial["passed"],
                        "returncode": trial["returncode"],
                        "duration_ms": trial["duration_ms"],
                        "rejected_mutation_functions": trial.get(
                            "rejected_mutation_functions",
                            0,
                        ),
                        "expected_mutation_functions": trial.get(
                            "expected_mutation_functions",
                            0,
                        ),
                    }
                    for trial in trials
                },
            }
        )

    if cancelled:
        live.status("cancelled", None)
        return 130

    passed_targets = sum(item["passed"] for item in target_summaries)
    final_file_count, final_tree_sha256 = (
        generate_campaign.generated_harness_tree_digest(rows)
    )
    artifact_tree_unchanged = (
        final_file_count == generated_file_count
        and final_tree_sha256 == generated_tree_sha256
    )
    if not artifact_tree_unchanged:
        live.failed += 1
    summary = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "passed" if live.failed == 0 and live.done == total else "failed",
        "expected_trials": total,
        "completed_trials": live.done,
        "failed_trials": live.failed,
        "selected_targets": len(rows),
        "passed_targets": passed_targets,
        "implementation_actual_verus_verified": sum(
            item["trials"]["implementation_actual_verus"]["passed"]
            for item in target_summaries
        ),
        "completeness_actual_verus_verified": sum(
            item["trials"]["completeness_actual_verus"]["passed"]
            for item in target_summaries
        ),
        "mutations_rejected": sum(
            item["trials"]["mutation_actual_verus"]["passed"]
            for item in target_summaries
        ),
        "mutation_functions_rejected": sum(
            item["trials"]["mutation_actual_verus"].get(
                "rejected_mutation_functions",
                0,
            )
            for item in target_summaries
        ),
        "expected_mutation_functions": sum(
            item["trials"]["mutation_actual_verus"].get(
                "expected_mutation_functions",
                0,
            )
            for item in target_summaries
        ),
        "generated_spec_no_verify": spec_record["passed"],
        "artifact_tree_unchanged": artifact_tree_unchanged,
        "generated_harness_file_count": final_file_count,
        "generated_harness_tree_sha256": final_tree_sha256,
        "targets": target_summaries,
        "completed_at": now(),
    }
    atomic_json(live.root / "summary.json", summary)
    latest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "run_root": str(live.root.relative_to(ROOT)),
        "summary": str((live.root / "summary.json").relative_to(ROOT)),
        "summary_sha256": sha256_file(live.root / "summary.json"),
        "status": summary["status"],
    }
    atomic_json(EVIDENCE_ROOT / "latest_manifest.json", latest)

    aggregate_path = ROOT / "proof_inventory/aggregate_coverage.json"
    aggregate = json.loads(aggregate_path.read_text())
    aggregate.update(
        {
            "actual_verus_verified": summary["implementation_actual_verus_verified"],
            "completeness_verified": summary["completeness_actual_verus_verified"],
            "mutation_rejected": summary["mutations_rejected"],
            "mutation_functions_rejected": summary[
                "mutation_functions_rejected"
            ],
            "pending": len(rows) - passed_targets,
            "evidence_status": summary["status"],
            "active_verus_run_id": args.run_id,
        }
    )
    atomic_json(aggregate_path, aggregate)
    audit_path = ROOT / "verification/audits/proof_evidence_audit.json"
    audit = json.loads(audit_path.read_text())
    audit.update(
        {
            "status": "passed" if summary["status"] == "passed" else "failed",
            "active_run_id": args.run_id,
            "verified": summary["implementation_actual_verus_verified"],
            "complete": summary["completeness_actual_verus_verified"],
            "mutation_rejected": summary["mutations_rejected"],
        }
    )
    atomic_json(audit_path, audit)
    live.status("completed" if summary["status"] == "passed" else "failed", None)
    live.event(
        "run_completed" if summary["status"] == "passed" else "run_failed",
        status=summary["status"],
        message=(
            f"targets={passed_targets}/{len(rows)} trials={live.done}/{total} "
            f"failed={live.failed}"
        ),
    )
    print(json.dumps(summary, indent=2))
    return 0 if summary["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
