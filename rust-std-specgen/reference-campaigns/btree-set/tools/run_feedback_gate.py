#!/usr/bin/env python3
"""Run seeded feedback determinism for every generated BTreeSet contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DRIVER = ROOT.parent / "run_rust_std_spec_feedback.py"
FEEDBACK_ROOT = ROOT / "verification/evidence/btree_set_feedback_determinism"
MANIFEST = ROOT / "specgen/btree_set_stable_manifest.json"
SEEDS = ROOT / "specgen/btree_set_seed_candidates.json"
CONTRACTS = ROOT / "specgen/existing_contract_context.json"
VSTD = ROOT.parent / "verus/source/vstd"
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
Z3 = ROOT.parent / "verus/source/target-verus/release/z3"
PYTHON = ROOT.parent / ".venv/bin/python"
VERUS_SUCCESS = re.compile(r"verification results::\s+\d+ verified, 0 errors")
APPEND_TARGET = "alloc::collections::btree_set::BTreeSet::<T, A>::append"


def checker_limitation(
    target: str | None,
    raw_checker_status: str,
    determinism_stderr: str,
) -> str | None:
    if (
        raw_checker_status == "verus_error"
        and "generated ill-typed AIR code" in determinism_stderr
        and "IntoIterator./Item" in determinism_stderr
        and (
            " as core::iter::Extend<" in str(target)
            or " as core::iter::FromIterator<" in str(target)
        )
    ):
        return "verus-intoiterator-associated-item-air"
    if (
        target == APPEND_TARGET
        and raw_checker_status == "verus_error"
        and "trait bound `T: std::cmp::Ord` is not satisfied"
        in determinism_stderr
        and "vstd::laws_cmp::obeys_cmp" in determinism_stderr
        and "det___rust_std_candidate_equal" in determinism_stderr
    ):
        return "spec-determinism-dropped-duplicate-method-where-clause"
    return None


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def append_jsonl(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def run_module_spec_mode(
    run_root: Path, name: str, *, no_verify: bool
) -> dict[str, Any]:
    source = ROOT / "specs/generated_btree_set_specs.rs"
    command = [str(VERUS), "--crate-type=lib"]
    if no_verify:
        command.append("--no-verify")
    command.append(str(source))
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=180,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    passed = result.returncode == 0 and (
        no_verify or VERUS_SUCCESS.search(result.stdout + result.stderr) is not None
    )
    evidence = run_root / "module_evidence"
    evidence.mkdir(exist_ok=True)
    (evidence / f"{name}.command").write_text(
        " ".join(command) + "\n", encoding="utf-8"
    )
    (evidence / f"{name}.stdout").write_text(result.stdout, encoding="utf-8")
    (evidence / f"{name}.stderr").write_text(result.stderr, encoding="utf-8")
    (evidence / f"{name}.rc").write_text(
        f"{result.returncode}\n", encoding="utf-8"
    )
    record = {
        "schema_version": 1,
        "name": name,
        "command": command,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256_file(source),
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "passed": passed,
        "completed_at": now(),
    }
    atomic_json(evidence / f"{name}.json", record)
    return record


def run_spec_determinism(
    run_root: Path,
    inventory_row: dict[str, Any],
) -> dict[str, Any]:
    source = (
        ROOT
        / "verification/spec_determinism_harnesses"
        / f"{inventory_row['target_id']}.rs"
    )
    command = [
        str(VERUS),
        "--crate-type=lib",
        "--triggers-mode",
        "silent",
        str(source),
    ]
    started = time.monotonic()
    result = subprocess.run(
        command,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=90,
    )
    duration_ms = int((time.monotonic() - started) * 1000)
    passed = (
        result.returncode == 0
        and VERUS_SUCCESS.search(result.stdout + result.stderr) is not None
    )
    evidence_root = run_root / "spec_determinism"
    evidence_root.mkdir(exist_ok=True)
    stem = inventory_row["target_id"]
    (evidence_root / f"{stem}.stdout").write_text(
        result.stdout, encoding="utf-8"
    )
    (evidence_root / f"{stem}.stderr").write_text(
        result.stderr, encoding="utf-8"
    )
    record = {
        "schema_version": 1,
        "target_id": stem,
        "canonical_target": inventory_row["canonical_target"],
        "contract_fingerprint": inventory_row["contract_fingerprint"],
        "accepted_requires_sha256": inventory_row[
            "accepted_requires_sha256"
        ],
        "accepted_clause_sha256": inventory_row["accepted_clause_sha256"],
        "command": command,
        "source": str(source.relative_to(ROOT)),
        "source_sha256": sha256_file(source),
        "returncode": result.returncode,
        "duration_ms": duration_ms,
        "passed": passed,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "completed_at": now(),
    }
    record_path = evidence_root / f"{stem}.json"
    atomic_json(record_path, record)
    record["evidence"] = str(record_path.relative_to(ROOT))
    return record


def write_status(
    path: Path,
    run_id: str,
    state: str,
    done: int,
    total: int,
    current: str | None,
    started: str,
) -> None:
    atomic_json(
        path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "status": state,
            "done": done,
            "total": total,
            "current": current,
            "started_at": started,
            "updated_at": now(),
        },
    )


def event(
    path: Path,
    run_id: str,
    name: str,
    done: int,
    total: int,
    **extra: Any,
) -> None:
    append_jsonl(
        path,
        {
            "timestamp": now(),
            "event": name,
            "run_id": run_id,
            "done": done,
            "total": total,
            "phase": "feedback_determinism",
            **extra,
        },
    )


def final_records(raw_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((raw_root / "targets").glob("*/summary.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        final = payload.get("final") or {}
        checker = final.get("checker") or {}
        typecheck = checker.get("typecheck") or {}
        determinism = checker.get("determinism") or {}
        round_result = path.parent / "round_00/round_result.json"
        det_stderr_path = path.parent / "round_00/det_stderr.txt"
        det_stderr = (
            det_stderr_path.read_text(encoding="utf-8")
            if det_stderr_path.is_file()
            else ""
        )
        raw_checker_status = determinism.get("status", "not_run")
        raw_r0_z3 = determinism.get("r0_z3", "not_run")
        limitation = checker_limitation(
            payload.get("target"),
            raw_checker_status,
            det_stderr,
        )
        records.append(
            {
                "target": payload.get("target"),
                "decision": (final.get("candidate") or {}).get("decision"),
                "contract_form": (final.get("candidate") or {}).get("contract_form"),
                "typecheck_returncode": typecheck.get("returncode"),
                "checker_status": (
                    "unsupported"
                    if limitation is not None
                    else raw_checker_status
                ),
                "r0_z3": (
                    "unsupported"
                    if limitation is not None
                    else raw_r0_z3
                ),
                "raw_checker_status": raw_checker_status,
                "raw_r0_z3": raw_r0_z3,
                "checker_limitation": limitation,
                "determinism_stderr": (
                    str(det_stderr_path.relative_to(ROOT))
                    if det_stderr_path.is_file()
                    else None
                ),
                "anti_vacuity_issues": final.get("anti_vacuity_issues") or [],
                "summary": str(path.relative_to(ROOT)),
                "round_result": (
                    str(round_result.relative_to(ROOT))
                    if round_result.is_file()
                    else None
                ),
            }
        )
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--jobs", type=int, default=8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    expected_targets = [item["target"] for item in manifest_payload["targets"]]
    total = len(expected_targets)
    run_root = FEEDBACK_ROOT / args.run_id
    if run_root.exists():
        raise RuntimeError(f"run directory already exists: {run_root}")
    raw_root = run_root / "feedback"
    raw_root.mkdir(parents=True)
    progress = run_root / "progress.jsonl"
    results = run_root / "run_results.jsonl"
    stdout_path = run_root / "stdout.log"
    stderr_path = run_root / "stderr.log"
    for path in (progress, results, stdout_path, stderr_path):
        path.touch()
    started = now()
    command = [
        str(PYTHON),
        str(DRIVER),
        "--manifest",
        str(MANIFEST),
        "--contracts",
        str(CONTRACTS),
        "--vstd-root",
        str(VSTD),
        "--verus-bin",
        str(VERUS),
        "--z3-path",
        str(Z3),
        "--out",
        str(raw_root),
        "--jobs",
        str(args.jobs),
        "--seed-candidates",
        str(SEEDS),
        "--feedback-rounds",
        "0",
        "--check-timeout",
        "90",
        "--rlimit",
        "20",
    ]
    atomic_json(
        run_root / "manifest.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "objective": (
                f"Typecheck and determinism-check all {total} generated "
                "BTreeSet contracts through run_rust_std_spec_feedback.py"
            ),
            "command": command,
            "expected_trials": total,
            "model_routes": ["seeded/no-model-call"],
            "budget": {
                "max_model_calls": 0,
                "max_targets": total,
                "per_check_timeout_seconds": 90,
            },
            "source_snapshot": {
                "manifest": str(MANIFEST.relative_to(ROOT)),
                "manifest_sha256": sha256_file(MANIFEST),
                "seeds": str(SEEDS.relative_to(ROOT)),
                "seeds_sha256": sha256_file(SEEDS),
                "contracts": str(CONTRACTS.relative_to(ROOT)),
                "contracts_sha256": sha256_file(CONTRACTS),
                "spec_determinism_manifest": (
                    "verification/spec_determinism_harnesses/manifest.json"
                ),
                "spec_determinism_manifest_sha256": sha256_file(
                    ROOT / "verification/spec_determinism_harnesses/manifest.json"
                ),
            },
            "created_at": started,
        },
    )
    write_status(run_root / "status.json", args.run_id, "pending", 0, total, None, started)
    event(progress, args.run_id, "run_started", 0, total)
    module_no_verify = run_module_spec_mode(
        run_root, "generated_spec_no_verify", no_verify=True
    )
    module_actual = run_module_spec_mode(
        run_root, "generated_spec_actual_verus", no_verify=False
    )
    module_modes_passed = (
        module_no_verify["passed"] and module_actual["passed"]
    )
    event(
        progress,
        args.run_id,
        "module_spec_modes_done",
        0,
        total,
        passed=module_modes_passed,
    )

    with (
        stdout_path.open("w", encoding="utf-8") as stdout,
        stderr_path.open("w", encoding="utf-8") as stderr,
    ):
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        seen: set[Path] = set()
        last_heartbeat = time.monotonic()
        cancelled = False
        while process.poll() is None:
            if (run_root / "STOP").exists():
                process.terminate()
                try:
                    process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
                cancelled = True
                break
            for summary_path in sorted((raw_root / "targets").glob("*/summary.json")):
                if summary_path in seen:
                    continue
                seen.add(summary_path)
                payload = json.loads(summary_path.read_text(encoding="utf-8"))
                append_jsonl(
                    results,
                    {
                        "target": payload.get("target"),
                        "summary": str(summary_path.relative_to(ROOT)),
                        "completed_at": now(),
                    },
                )
                event(
                    progress,
                    args.run_id,
                    "trial_done",
                    len(seen),
                    total,
                    target=payload.get("target"),
                )
                write_status(
                    run_root / "status.json",
                    args.run_id,
                    "running",
                    len(seen),
                    total,
                    payload.get("target"),
                    started,
                )
            if time.monotonic() - last_heartbeat >= 30:
                event(
                    progress,
                    args.run_id,
                    "heartbeat",
                    len(seen),
                    total,
                    worker_pid=process.pid,
                )
                last_heartbeat = time.monotonic()
            time.sleep(1)

    if cancelled:
        write_status(
            run_root / "status.json",
            args.run_id,
            "cancelled",
            len(seen),
            total,
            None,
            started,
        )
        event(progress, args.run_id, "run_cancelled", len(seen), total)
        return 130

    records = final_records(raw_root)
    target_names = {record["target"] for record in records}
    missing = sorted(set(expected_targets) - target_names)
    extra = sorted(target_names - set(expected_targets))
    typecheck_failures = [
        record["target"] for record in records if record["typecheck_returncode"] != 0
    ]
    assume_records = [
        record
        for record in records
        if record["contract_form"] == "assume_specification"
    ]
    checker_errors = [
        record["target"]
        for record in assume_records
        if record["checker_status"] in {"verus_error", "exception", "not_run"}
    ]
    sat = [record["target"] for record in assume_records if record["r0_z3"] == "sat"]
    adjudicated = [
        record["target"]
        for record in assume_records
        if record["r0_z3"] in {"unknown", "unsupported"}
    ]
    unresolved = [
        record["target"]
        for record in assume_records
        if record["r0_z3"] in {"not-run", "not_run"}
    ]
    missing_round_results = [
        record["target"] for record in records if record["round_result"] is None
    ]
    adjudication_path = run_root / "checker_capability_adjudications.json"
    inventory_rows = json.loads(
        (ROOT / "inventory/btree_set_exec_fn_inventory.json").read_text(
            encoding="utf-8"
        )
    )["rows"]
    inventory_by_target = {
        row["canonical_target"]: row for row in inventory_rows
    }
    determinism_records: dict[str, dict[str, Any]] = {}
    if adjudicated:
        with ThreadPoolExecutor(
            max_workers=max(1, min(args.jobs, len(adjudicated)))
        ) as executor:
            futures = {
                executor.submit(
                    run_spec_determinism,
                    run_root,
                    inventory_by_target[target],
                ): target
                for target in adjudicated
            }
            for future in as_completed(futures):
                target = futures[future]
                determinism_records[target] = future.result()
                event(
                    progress,
                    args.run_id,
                    "spec_determinism_done",
                    len(seen),
                    total,
                    target=target,
                    passed=determinism_records[target]["passed"],
                )
    determinism_failures = sorted(
        target
        for target, record in determinism_records.items()
        if not record["passed"]
    )
    strict_pass = not (
        not module_modes_passed
        or process.returncode != 0
        or missing
        or extra
        or typecheck_failures
        or checker_errors
        or sat
        or unresolved
        or missing_round_results
        or set(determinism_records) != set(adjudicated)
        or determinism_failures
    )
    atomic_json(
        adjudication_path,
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_set",
            "policy": (
                "UNKNOWN/unsupported from the generic checker is not accepted by "
                "itself; each such row is resolved in this specification stage by "
                "an actual-Verus proof that directly assumes every hashed accepted "
                "clause for two candidates and proves exact observable equality"
            ),
            "adjudicated_count": len(adjudicated),
            "unresolved_count": len(unresolved),
            "rows": [
                {
                    "target": target,
                    "feedback_status": next(
                        record["r0_z3"]
                        for record in assume_records
                        if record["target"] == target
                    ),
                    "raw_feedback_status": next(
                        record["raw_r0_z3"]
                        for record in assume_records
                        if record["target"] == target
                    ),
                    "checker_limitation": next(
                        record["checker_limitation"]
                        for record in assume_records
                        if record["target"] == target
                    ),
                    "raw_error_evidence": next(
                        record["determinism_stderr"]
                        for record in assume_records
                        if record["target"] == target
                    ),
                    "equivalence": "exact_observable_equality",
                    "feedback_acceptance_evidence": True,
                    "contract_fingerprint": inventory_by_target[target][
                        "contract_fingerprint"
                    ],
                    "source": {
                        "file": inventory_by_target[target]["source_file"],
                        "line_start": inventory_by_target[target]["line_start"],
                        "line_end": inventory_by_target[target]["line_end"],
                        "sha256": inventory_by_target[target]["source_sha256"],
                    },
                    "principal_behavior": inventory_by_target[target][
                        "principal_behavior"
                    ],
                    "spec_determinism_evidence": determinism_records[target][
                        "evidence"
                    ],
                    "spec_determinism_source_sha256": determinism_records[target][
                        "source_sha256"
                    ],
                    "required_followup": None,
                }
                for target in adjudicated
            ],
        },
    )
    summary = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": "passed" if strict_pass else "failed",
        "driver_returncode": process.returncode,
        "generated_spec_no_verify": module_no_verify["passed"],
        "generated_spec_actual_verus": module_actual["passed"],
        "module_spec_evidence": "module_evidence",
        "expected_targets": total,
        "completed_targets": len(records),
        "missing_targets": missing,
        "extra_targets": extra,
        "typecheck_passed": len(records) - len(typecheck_failures),
        "typecheck_failures": typecheck_failures,
        "assume_specification_targets": len(assume_records),
        "non_assume_contract_targets": total - len(assume_records),
        "checker_status_counts": dict(
            sorted(Counter(record["checker_status"] for record in records).items())
        ),
        "r0_z3_counts": dict(
            sorted(Counter(record["r0_z3"] for record in records).items())
        ),
        "checker_errors": checker_errors,
        "sat_targets": sat,
        "checker_capability_adjudicated_targets": adjudicated,
        "spec_determinism_proved_targets": sorted(determinism_records),
        "spec_determinism_failures": determinism_failures,
        "checker_capability_adjudication": str(adjudication_path.relative_to(ROOT)),
        "unresolved_targets": unresolved,
        "missing_round_results": missing_round_results,
        "records": records,
        "completed_at": now(),
    }
    atomic_json(run_root / "summary.json", summary)
    atomic_json(
        FEEDBACK_ROOT / "latest_manifest.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "run_root": str(run_root.relative_to(ROOT)),
            "summary": str((run_root / "summary.json").relative_to(ROOT)),
            "summary_sha256": sha256_file(run_root / "summary.json"),
            "batch_summary": str((raw_root / "batch_summary.json").relative_to(ROOT)),
            "checker_capability_adjudication": str(
                adjudication_path.relative_to(ROOT)
            ),
            "status": summary["status"],
        },
    )
    atomic_json(
        ROOT / "verification/audits/feedback_determinism_audit.json",
        {
            "schema_version": 1,
            "module": "alloc::collections::btree_set",
            "status": "passed" if strict_pass else "failed",
            "active_run_id": args.run_id,
            "expected_generated_targets": total,
            "typecheck_passed": summary["typecheck_passed"],
            "checker_status_counts": summary["checker_status_counts"],
            "r0_z3_counts": summary["r0_z3_counts"],
            "sat_targets": sat,
            "checker_capability_adjudicated_targets": adjudicated,
            "spec_determinism_proved_targets": sorted(determinism_records),
            "spec_determinism_failures": determinism_failures,
            "unresolved_targets": unresolved,
            "missing_round_results": missing_round_results,
        },
    )
    pipeline_path = ROOT / "research/PIPELINE_STATE.json"
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    pipeline["stages"]["specification"].update(
        {
            "status": (
                "feedback_passed_pending_review" if strict_pass else "feedback_failed"
            ),
            "feedback_run_id": args.run_id,
            "feedback_typecheck_passed": summary["typecheck_passed"],
            "feedback_checker_capability_adjudicated": len(adjudicated),
            "feedback_unresolved": len(unresolved),
        }
    )
    atomic_json(pipeline_path, pipeline)
    write_status(
        run_root / "status.json",
        args.run_id,
        "completed" if strict_pass else "failed",
        len(records),
        total,
        None,
        started,
    )
    event(
        progress,
        args.run_id,
        "run_completed" if strict_pass else "run_failed",
        len(records),
        total,
        status=summary["status"],
    )
    print(
        json.dumps(
            {
                "run_id": args.run_id,
                "status": summary["status"],
                "expected_targets": total,
                "typecheck_passed": summary["typecheck_passed"],
                "sat": len(sat),
                "unresolved": len(unresolved),
                "checker_errors": len(checker_errors),
                "spec_determinism_proved": len(determinism_records),
                "spec_determinism_failures": len(determinism_failures),
            },
            sort_keys=True,
        )
    )
    return 0 if strict_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
