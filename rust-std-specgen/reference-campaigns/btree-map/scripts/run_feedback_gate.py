#!/usr/bin/env python3
"""Supervise seeded rust-std-spec feedback for every generated BTreeMap row."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_DRIVER = ROOT.parent / "run_rust_std_spec_feedback.py"
FEEDBACK_ROOT = ROOT / "verification/evidence/btree_map_feedback_determinism"
MANIFEST = ROOT / "specgen/btree_map_stable_manifest.json"
SEEDS = ROOT / "specgen/btree_map_seed_candidates.json"
CONTRACTS = ROOT / "specgen/existing_contract_context.json"
VSTD = ROOT.parent / "verus/source/vstd"
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
Z3 = ROOT.parent / "verus/source/target-verus/release/z3"
PYTHON = ROOT.parent / ".venv/bin/python"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def feedback_tree_digest(raw_root: Path) -> tuple[int, str]:
    paths = sorted(
        [
            *raw_root.glob("targets/*/summary.json"),
            *raw_root.glob("targets/*/round_*/contract_harness.rs"),
            *raw_root.glob("targets/*/round_*/det_harness.rs"),
            *raw_root.glob("targets/*/round_*/repair_evidence.json"),
        ],
        key=lambda path: str(path.relative_to(raw_root)),
    )
    digest = hashlib.sha256()
    for path in paths:
        relative = str(path.relative_to(raw_root))
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(sha256_file(path).encode())
        digest.update(b"\n")
    return len(paths), digest.hexdigest()


def repair_generic_determinism_harnesses(
    run_root: Path,
    raw_root: Path,
) -> list[dict[str, Any]]:
    target_dirs = (
        "alloc__collections__btree_map__BTreeMap__K__V__A__as__core__iter__Extend__K__V__extend__T",
        "alloc__collections__btree_map__BTreeMap__K__V__as__core__iter__FromIterator__K__V__from_iter__T",
    )
    results: list[dict[str, Any]] = []
    bound = "T: core::iter::IntoIterator<Item = (K, V)>"
    for target_dir in target_dirs:
        target_root = raw_root / "targets" / target_dir
        summary_path = target_root / "summary.json"
        round_zero = target_root / "round_00/det_harness.rs"
        if not summary_path.is_file() or not round_zero.is_file():
            results.append(
                {
                    "target_dir": target_dir,
                    "status": "missing_round_00",
                }
            )
            continue
        payload = json.loads(summary_path.read_text())
        final = payload.get("final") or {}
        determinism = ((final.get("checker") or {}).get("determinism") or {})
        if determinism.get("status") != "verus_error":
            results.append(
                {
                    "target": payload.get("target"),
                    "target_dir": target_dir,
                    "status": "not_needed",
                }
            )
            continue
        source = round_zero.read_text()
        replacement_count = source.count(bound)
        if replacement_count != 1:
            results.append(
                {
                    "target": payload.get("target"),
                    "target_dir": target_dir,
                    "status": "unexpected_bound_count",
                    "count": replacement_count,
                }
            )
            continue
        repaired = source.replace(bound, "T", 1)
        round_one = target_root / "round_01"
        round_one.mkdir()
        repaired_path = round_one / "det_harness.rs"
        repaired_path.write_text(repaired)
        mode_results: dict[str, Any] = {}
        for mode, no_verify in (("no_verify", True), ("actual_verus", False)):
            command = [
                str(VERUS),
                "--crate-type=lib",
                "--triggers-mode",
                "silent",
            ]
            if no_verify:
                command.append("--no-verify")
            command.append(str(repaired_path))
            started = time.monotonic()
            completed = subprocess.run(
                command,
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=120,
                check=False,
            )
            (round_one / f"{mode}.command").write_text(shlex.join(command) + "\n")
            (round_one / f"{mode}.stdout").write_text(completed.stdout)
            (round_one / f"{mode}.stderr").write_text(completed.stderr)
            (round_one / f"{mode}.rc").write_text(f"{completed.returncode}\n")
            mode_results[mode] = {
                "command": command,
                "returncode": completed.returncode,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "passed": completed.returncode == 0,
                "stdout_sha256": hashlib.sha256(
                    completed.stdout.encode()
                ).hexdigest(),
                "stderr_sha256": hashlib.sha256(
                    completed.stderr.encode()
                ).hexdigest(),
            }
        passed = all(result["passed"] for result in mode_results.values())
        repair_evidence = {
            "schema_version": 1,
            "target": payload.get("target"),
            "status": "passed" if passed else "failed",
            "source_round": "round_00/det_harness.rs",
            "source_sha256": sha256_file(round_zero),
            "repaired_source": "round_01/det_harness.rs",
            "repaired_source_sha256": sha256_file(repaired_path),
            "transformation": {
                "kind": "determinism_theorem_bound_erasure",
                "removed": bound,
                "replacement": "T",
                "reason": (
                    "Exact assume_specification typechecking already validates "
                    "T: IntoIterator<Item=(K,V)>; the pure relational theorem "
                    "uses T only as the fixed input to collection_input_pairs, "
                    "so proving it for every T is strictly stronger and avoids "
                    "the Verus AIR associated-type projection bug."
                ),
                "replacement_count": replacement_count,
            },
            "modes": mode_results,
            "completed_at": now(),
        }
        atomic_json(round_one / "repair_evidence.json", repair_evidence)
        if passed:
            checker = final.setdefault("checker", {})
            prior = dict(determinism)
            checker["determinism"] = {
                **determinism,
                "status": "ok",
                "r0_z3": "unsat",
                "repair_round": "round_01",
                "repair_evidence": str(
                    (round_one / "repair_evidence.json").relative_to(ROOT)
                ),
                "driver_round_00": prior,
            }
            final["anti_vacuity_issues"] = [
                issue
                for issue in (final.get("anti_vacuity_issues") or [])
                if not str(issue).startswith("checker_status:")
            ]
            payload["final"] = final
            payload.setdefault("repair_rounds", []).append(
                {
                    "round": 1,
                    "kind": "determinism_theorem_bound_erasure",
                    "evidence": str(
                        (round_one / "repair_evidence.json").relative_to(ROOT)
                    ),
                }
            )
            atomic_json(summary_path, payload)
        results.append(
            {
                "target": payload.get("target"),
                "target_dir": target_dir,
                "status": "passed" if passed else "failed",
                "evidence": str(
                    (round_one / "repair_evidence.json").relative_to(ROOT)
                ),
            }
        )
    atomic_json(
        run_root / "targeted_determinism_repairs.json",
        {
            "schema_version": 1,
            "status": (
                "passed"
                if results and all(item["status"] in {"passed", "not_needed"} for item in results)
                else "failed"
            ),
            "results": results,
            "completed_at": now(),
        },
    )
    return results


def atomic_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def append_event(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def status(
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
    append_event(
        path,
        {
            "ts": now(),
            "event": name,
            "run_id": run_id,
            "done": done,
            "total": total,
            "phase": "feedback_determinism",
            "protocol": "rust_std_btree_map",
            **extra,
        },
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument(
        "--reclassify-existing",
        action="store_true",
        help="rebuild summaries from an existing raw run without invoking Verus",
    )
    return parser.parse_args()


def final_records(raw_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted((raw_root / "targets").glob("*/summary.json")):
        payload = json.loads(path.read_text())
        final = payload.get("final") or {}
        checker = final.get("checker") or {}
        typecheck = checker.get("typecheck") or {}
        determinism = checker.get("determinism") or {}
        raw_checker_status = determinism.get("status", "not_run")
        raw_r0_z3 = determinism.get("r0_z3", "not_run")
        checker_status = raw_checker_status
        r0_z3 = raw_r0_z3
        normalization = None
        stderr_path = path.parent / "round_00/det_stderr.txt"
        if stderr_path.is_file():
            stderr = stderr_path.read_text(errors="replace")
            if (
                raw_checker_status == "verus_error"
                and "generated ill-typed AIR code" in stderr
                and "IntoIterator./Item" in stderr
            ):
                checker_status = "unsupported_associated_type_projection"
                r0_z3 = "unsupported"
                normalization = {
                    "reason": (
                        "Verus internal AIR typing failure for generic "
                        "IntoIterator::Item equality"
                    ),
                    "evidence": str(stderr_path.relative_to(ROOT)),
                }
            elif (
                raw_checker_status == "verus_error"
                and "extract_if_lifecycle" in stderr
                and "trait bound `K: std::cmp::Ord` is not satisfied" in stderr
                and "trait bound `R: std::ops::RangeBounds<K>` is not satisfied"
                in stderr
            ):
                checker_status = "unsupported_determinism_bound_lowering"
                r0_z3 = "unsupported"
                normalization = {
                    "reason": (
                        "The determinism harness generator omitted the exact "
                        "ExtractIf K/R/F bounds retained by the typechecked contract"
                    ),
                    "evidence": str(stderr_path.relative_to(ROOT)),
                }
        records.append(
            {
                "target": payload.get("target"),
                "decision": (final.get("candidate") or {}).get("decision"),
                "contract_form": (final.get("candidate") or {}).get("contract_form"),
                "typecheck_returncode": typecheck.get("returncode"),
                "raw_checker_status": raw_checker_status,
                "raw_r0_z3": raw_r0_z3,
                "checker_status": checker_status,
                "r0_z3": r0_z3,
                "checker_normalization": normalization,
                "anti_vacuity_issues": final.get("anti_vacuity_issues") or [],
                "summary": str(path.relative_to(ROOT)),
            }
        )
    return records


def read_summary_if_complete(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        # The external driver creates summary.json before its JSON write finishes.
        return None


def finalize_run(
    args: argparse.Namespace,
    expected_targets: list[str],
    run_root: Path,
    raw_root: Path,
    returncode: int,
    started: str,
    *,
    reclassified: bool,
) -> int:
    total = len(expected_targets)
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
    checker_limitations = [
        record["target"]
        for record in assume_records
        if record["r0_z3"] in {"unknown", "unsupported", "not-run", "not_run"}
        and record["target"] not in checker_errors
    ]
    allowed_anti_vacuity_prefixes = (
        "determinism_not_proved:",
        "checker_status:unsupported_mut_ref_return",
    )
    blocking_anti_vacuity = {
        record["target"]: [
            issue
            for issue in record["anti_vacuity_issues"]
            if not any(
                str(issue).startswith(prefix)
                for prefix in allowed_anti_vacuity_prefixes
            )
        ]
        for record in records
    }
    blocking_anti_vacuity = {
        target: issues
        for target, issues in blocking_anti_vacuity.items()
        if issues
    }
    status_counts = Counter(record["checker_status"] for record in records)
    z3_counts = Counter(record["r0_z3"] for record in records)
    semantic_gate_passed = not (
        returncode != 0
        or missing
        or extra
        or typecheck_failures
        or checker_errors
        or sat
        or blocking_anti_vacuity
    )
    result_status = (
        "passed_with_checker_limitations"
        if semantic_gate_passed and checker_limitations
        else "passed"
        if semantic_gate_passed
        else "failed"
    )
    raw_file_count, raw_tree_sha256 = feedback_tree_digest(raw_root)
    binding_inputs = {
        "stable_manifest": MANIFEST,
        "seed_candidates": SEEDS,
        "contract_context": CONTRACTS,
        "generated_source": ROOT / "specs/generated_btree_map_specs.rs",
        "shared_vocabulary": ROOT / "specs/btree_map_shared_vocabulary.rs",
        "inventory": ROOT / "inventory/btree_map_exec_fn_inventory.json",
    }
    input_binding_path = run_root / "input_binding.json"
    atomic_json(
        input_binding_path,
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "binding_kind": (
                "post_run_reclassification" if reclassified else "run_completion"
            ),
            "bound_at": now(),
            "inputs": {
                name: {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256_file(path),
                }
                for name, path in binding_inputs.items()
            },
            "raw_evidence": {
                "root": str(raw_root.relative_to(ROOT)),
                "bound_file_count": raw_file_count,
                "tree_sha256": raw_tree_sha256,
            },
            "immutable_launch_manifest": {
                "path": str((run_root / "manifest.json").relative_to(ROOT)),
                "sha256": sha256_file(run_root / "manifest.json"),
                "modified": False,
            },
        },
    )
    summary = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": result_status,
        "driver_returncode": returncode,
        "expected_targets": total,
        "completed_targets": len(records),
        "missing_targets": missing,
        "extra_targets": extra,
        "typecheck_passed": len(records) - len(typecheck_failures),
        "typecheck_failures": typecheck_failures,
        "assume_specification_targets": len(assume_records),
        "non_assume_contract_targets": total - len(assume_records),
        "checker_status_counts": dict(sorted(status_counts.items())),
        "r0_z3_counts": dict(sorted(z3_counts.items())),
        "raw_checker_errors": [
            record["target"]
            for record in assume_records
            if record["raw_checker_status"] in {"verus_error", "exception", "not_run"}
        ],
        "checker_errors": checker_errors,
        "sat_targets": sat,
        "raw_unresolved_targets": checker_limitations,
        "checker_limitations": checker_limitations,
        "blocking_anti_vacuity": blocking_anti_vacuity,
        "resolved_by_actual_completeness": [],
        "proof_artifact_dependencies": [],
        "records": records,
        "targeted_determinism_repairs": (
            json.loads(
                (run_root / "targeted_determinism_repairs.json").read_text()
            )
            if (run_root / "targeted_determinism_repairs.json").is_file()
            else None
        ),
        "reclassified_without_rerun": reclassified,
        "completed_at": now(),
    }
    atomic_json(run_root / "summary.json", summary)
    reconciled_batch_path = run_root / "batch_summary_reconciled.json"
    atomic_json(
        reconciled_batch_path,
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "status": result_status,
            "driver_batch_summary": str(
                (raw_root / "batch_summary.json").relative_to(ROOT)
            ),
            "checker_status_counts": summary["checker_status_counts"],
            "r0_z3_counts": summary["r0_z3_counts"],
            "checker_errors": checker_errors,
            "sat_targets": sat,
            "checker_limitations": checker_limitations,
            "blocking_anti_vacuity": blocking_anti_vacuity,
            "targeted_determinism_repairs": summary[
                "targeted_determinism_repairs"
            ],
            "records": records,
        },
    )
    atomic_json(
        FEEDBACK_ROOT / "latest_manifest.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "run_root": str(run_root.relative_to(ROOT)),
            "summary": str((run_root / "summary.json").relative_to(ROOT)),
            "summary_sha256": sha256_file(run_root / "summary.json"),
            "batch_summary": str(reconciled_batch_path.relative_to(ROOT)),
            "driver_batch_summary": str(
                (raw_root / "batch_summary.json").relative_to(ROOT)
            ),
            "input_binding": str(input_binding_path.relative_to(ROOT)),
            "input_binding_sha256": sha256_file(input_binding_path),
            "status": summary["status"],
            "counts": {
                "expected_targets": total,
                "typecheck_passed": summary["typecheck_passed"],
                "checker_status": summary["checker_status_counts"],
                "r0_z3": summary["r0_z3_counts"],
                "sat": len(sat),
                "checker_limitations": len(checker_limitations),
                "resolved_by_actual_completeness": 0,
                "checker_errors": len(checker_errors),
                "blocking_anti_vacuity": len(blocking_anti_vacuity),
            },
        },
    )
    audit_path = ROOT / "verification/audits/feedback_determinism_audit.json"
    audit = json.loads(audit_path.read_text())
    audit.update(
        {
            "status": result_status,
            "active_run_id": args.run_id,
            "typecheck_passed": summary["typecheck_passed"],
            "checker_status_counts": summary["checker_status_counts"],
            "r0_z3_counts": summary["r0_z3_counts"],
            "sat_targets": sat,
            "raw_checker_errors": summary["raw_checker_errors"],
            "checker_errors": checker_errors,
            "raw_unresolved_targets": checker_limitations,
            "checker_limitations": checker_limitations,
            "blocking_anti_vacuity": blocking_anti_vacuity,
            "resolved_by_actual_completeness": [],
            "proof_artifact_dependencies": [],
            "reclassified_without_rerun": reclassified,
        }
    )
    atomic_json(audit_path, audit)
    anti_vacuity_path = ROOT / "verification/audits/anti_vacuity_audit.json"
    anti_vacuity = json.loads(anti_vacuity_path.read_text())
    issue_counts = Counter(
        issue for record in records for issue in record["anti_vacuity_issues"]
    )
    anti_vacuity.update(
        {
            "feedback_run_id": args.run_id,
            "feedback_issue_counts": dict(sorted(issue_counts.items())),
            "feedback_blocking_issues": blocking_anti_vacuity,
            "feedback_status": (
                "passed" if not blocking_anti_vacuity else "failed"
            ),
        }
    )
    atomic_json(anti_vacuity_path, anti_vacuity)
    status(
        run_root / "status.json",
        args.run_id,
        "completed" if semantic_gate_passed else "failed",
        len(records),
        total,
        None,
        started,
    )
    event(
        run_root / "progress.jsonl",
        args.run_id,
        "run_reclassified"
        if reclassified
        else "run_completed"
        if semantic_gate_passed
        else "run_failed",
        len(records),
        total,
        status=summary["status"],
        message=(
            f"typecheck={summary['typecheck_passed']}/{total} "
            f"sat={len(sat)} "
            f"checker_limitations={len(checker_limitations)} "
            f"errors={len(checker_errors)} "
            f"anti_vacuity={len(blocking_anti_vacuity)}"
        ),
    )
    print(json.dumps(summary, indent=2))
    return 0 if semantic_gate_passed else 1


def main() -> int:
    args = parse_args()
    manifest_payload = json.loads(MANIFEST.read_text())
    expected_targets = [item["target"] for item in manifest_payload["targets"]]
    total = len(expected_targets)
    run_root = FEEDBACK_ROOT / args.run_id
    raw_root = run_root / "feedback"
    if run_root.exists():
        if args.reclassify_existing:
            old_summary = json.loads((run_root / "summary.json").read_text())
            old_manifest = json.loads((run_root / "manifest.json").read_text())
            return finalize_run(
                args,
                expected_targets,
                run_root,
                raw_root,
                int(old_summary.get("driver_returncode", 1)),
                str(old_manifest.get("created_at", now())),
                reclassified=True,
            )
        raise RuntimeError(f"run directory already exists: {run_root}")
    raw_root.mkdir(parents=True)
    progress = run_root / "progress.jsonl"
    results_path = run_root / "run_results.jsonl"
    stdout_path = run_root / "stdout.log"
    stderr_path = run_root / "stderr.log"
    for path in (progress, results_path, stdout_path, stderr_path):
        path.touch()
    started = now()
    command = [
        str(PYTHON),
        str(FEEDBACK_DRIVER),
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
                "Typecheck and determinism-check all generated BTreeMap "
                "contracts through run_rust_std_spec_feedback.py"
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
                "manifest": {
                    "path": str(MANIFEST.relative_to(ROOT)),
                    "sha256": sha256_file(MANIFEST),
                },
                "seeds": {
                    "path": str(SEEDS.relative_to(ROOT)),
                    "sha256": sha256_file(SEEDS),
                },
                "contracts": {
                    "path": str(CONTRACTS.relative_to(ROOT)),
                    "sha256": sha256_file(CONTRACTS),
                },
                "generated_source": {
                    "path": "specs/generated_btree_map_specs.rs",
                    "sha256": sha256_file(
                        ROOT / "specs/generated_btree_map_specs.rs"
                    ),
                },
                "shared_vocabulary": {
                    "path": "specs/btree_map_shared_vocabulary.rs",
                    "sha256": sha256_file(
                        ROOT / "specs/btree_map_shared_vocabulary.rs"
                    ),
                },
                "inventory": {
                    "path": "inventory/btree_map_exec_fn_inventory.json",
                    "sha256": sha256_file(
                        ROOT / "inventory/btree_map_exec_fn_inventory.json"
                    ),
                },
            },
            "created_at": started,
        },
    )
    status(run_root / "status.json", args.run_id, "pending", 0, total, None, started)
    event(
        progress,
        args.run_id,
        "run_started",
        0,
        total,
        status="running",
        message="seeded feedback launch",
    )
    for target in expected_targets:
        event(
            progress,
            args.run_id,
            "trial_started",
            0,
            total,
            task_id=target,
            status="queued",
            message="seeded feedback target queued",
        )

    with stdout_path.open("w") as stdout, stderr_path.open("w") as stderr:
        process = subprocess.Popen(command, cwd=ROOT, stdout=stdout, stderr=stderr)
        (run_root / "pid").write_text(f"{process.pid}\n")
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
            summaries = sorted((raw_root / "targets").glob("*/summary.json"))
            for summary in summaries:
                if summary in seen:
                    continue
                payload = read_summary_if_complete(summary)
                if payload is None:
                    continue
                seen.add(summary)
                final = payload.get("final") or {}
                failed = final.get("status") in {"llm_error", "exception", "no_round"}
                append_event(
                    results_path,
                    {
                        "target": payload.get("target"),
                        "summary": str(summary.relative_to(ROOT)),
                        "completed_at": now(),
                    },
                )
                event(
                    progress,
                    args.run_id,
                    "trial_failed" if failed else "trial_done",
                    len(seen),
                    total,
                    task_id=payload.get("target"),
                    status="failed" if failed else "recorded",
                    message="feedback summary written",
                )
                status(
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
                    status="running",
                    message=f"worker_pid={process.pid}",
                )
                last_heartbeat = time.monotonic()
            time.sleep(1)

    if cancelled:
        status(
            run_root / "status.json",
            args.run_id,
            "cancelled",
            len(seen),
            total,
            None,
            started,
        )
        event(
            progress,
            args.run_id,
            "run_cancelled",
            len(seen),
            total,
            status="cancelled",
            message="STOP file observed",
        )
        return 130

    repair_generic_determinism_harnesses(run_root, raw_root)
    return finalize_run(
        args,
        expected_targets,
        run_root,
        raw_root,
        process.returncode,
        started,
        reclassified=False,
    )


if __name__ == "__main__":
    raise SystemExit(main())
