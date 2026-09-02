#!/usr/bin/env python3
"""Run complete omission-sensitive mutations over immutable proof snapshots."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_implementation_proofs as proof_runner


TARGETS = ROOT / "proof_inventory" / "targets.json"
LIVE_INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
MUTATION_ROOT = ROOT / "verification" / "mutations"
DEFAULT_VERUS = proof_runner.DEFAULT_VERUS
DEFAULT_Z3 = proof_runner.DEFAULT_Z3
VERIFICATION_RE = re.compile(
    r"verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors"
)
EXPECTED_REJECTION = (
    "postcondition not satisfied",
    "assertion failed",
    "precondition not satisfied",
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def compact_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value: Any) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n")


def target_dir(row: dict[str, Any]) -> Path:
    return proof_runner.target_dir(row)


def mutation_plan(
    manifest: dict[str, Any],
    proof_kind: str,
) -> dict[str, Any] | None:
    plans = mutation_plans(manifest, proof_kind)
    return plans[0] if plans else None


def mutation_plans(
    manifest: dict[str, Any],
    proof_kind: str,
) -> list[dict[str, Any]]:
    direct = manifest.get(f"{proof_kind}_mutations")
    if isinstance(direct, list):
        if direct and all(isinstance(value, dict) for value in direct):
            return list(direct)
        raise ValueError(f"{proof_kind}_mutations must be a non-empty object list")
    for key in (
        f"{proof_kind}_mutation",
        f"{proof_kind}_negative_probe",
    ):
        value = manifest.get(key)
        if isinstance(value, dict):
            return [value]
    mutations = manifest.get("mutations")
    if isinstance(mutations, dict):
        value = mutations.get(proof_kind)
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            if value and all(isinstance(item, dict) for item in value):
                return list(value)
            raise ValueError(
                f"mutations.{proof_kind} must be a non-empty object list"
            )
    return []


def mutation_id(
    plan: dict[str, Any],
    index: int,
    count: int,
) -> str:
    value = plan.get("id")
    if value is None and count == 1:
        return "default"
    if not isinstance(value, str) or not proof_runner.valid_run_id(value):
        raise ValueError(
            "multi-plan mutations require unique ids containing only letters, "
            "digits, dot, dash, or underscore"
        )
    return value


class Progress:
    def __init__(self, run_id: str, run_dir: Path, total: int) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.total = total
        self.completed = 0
        self.failed = 0
        self.cancelled = 0
        self.lock = threading.Lock()
        self.path = run_dir / "progress.jsonl"
        run_dir.mkdir(parents=True, exist_ok=False)
        self.path.touch()

    def stop_requested(self) -> bool:
        return (self.run_dir / "STOP").exists()

    def event(self, event: str, **details: Any) -> None:
        value = {
            "event": event,
            "run_id": self.run_id,
            "timestamp_utc": now(),
            **details,
        }
        with self.lock:
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(value, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

    def finish(self, status: str) -> None:
        with self.lock:
            self.completed += 1
            if status == "failed":
                self.failed += 1
            elif status == "cancelled":
                self.cancelled += 1
            atomic_json(
                self.run_dir / "status.json",
                {
                    "schema_version": 1,
                    "run_id": self.run_id,
                    "state": "running",
                    "completed_commands": self.completed,
                    "failed_commands": self.failed,
                    "cancelled_commands": self.cancelled,
                    "total_commands": self.total,
                    "updated_at_utc": now(),
                },
            )


def create_mutation(
    snapshot: Path,
    row: dict[str, Any],
    proof_kind: str,
    mutation_id_value: str,
    plan: dict[str, Any],
) -> tuple[Path, str, str]:
    source_relative = (
        target_dir(row).relative_to(ROOT) / f"{proof_kind}_proof.rs"
    )
    source = snapshot / source_relative
    text = source.read_text(encoding="utf-8")
    fragment = plan.get("fragment")
    replacement = plan.get("replacement")
    if not isinstance(fragment, str) or not fragment:
        raise ValueError(
            f"{row['row_id']} {proof_kind} mutation has no fragment"
        )
    if not isinstance(replacement, str):
        raise ValueError(
            f"{row['row_id']} {proof_kind} mutation has no replacement"
        )
    if text.count(fragment) != 1:
        raise ValueError(
            f"{row['row_id']} {proof_kind} mutation anchor count "
            f"is {text.count(fragment)}, expected 1"
        )
    baseline_hash = sha256(source)
    path = source.parent / (
        f"mutated_{proof_kind}_{mutation_id_value}_proof.rs"
    )
    path.write_text(text.replace(fragment, replacement, 1), encoding="utf-8")
    path.chmod(0o444)
    return path, baseline_hash, compact_hash(plan)


def run_command(
    progress: Progress,
    *,
    row: dict[str, Any],
    proof_kind: str,
    mutation_id_value: str,
    mode: str,
    path: Path,
    evidence_dir: Path,
    verus: Path,
    z3: Path,
    timeout: int,
) -> dict[str, Any]:
    command = [str(verus), str(path), "--crate-type=lib"]
    if mode == "no_verify":
        command.append("--no-verify")
    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(z3)
    phase = f"{proof_kind}_{mode}"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = evidence_dir / f"{phase}.stdout.txt"
    stderr_path = evidence_dir / f"{phase}.stderr.txt"
    command_path = evidence_dir / f"{phase}.command.txt"
    rc_path = evidence_dir / f"{phase}.rc.txt"
    result_path = evidence_dir / f"{phase}.json"
    atomic_text(
        command_path,
        f"VERUS_Z3_PATH={z3} " + " ".join(command) + "\n",
    )
    progress.event(
        "mutation_started",
        row_id=row["row_id"],
        target=row["target"],
        phase=phase,
        mutation_id=mutation_id_value,
    )
    started = time.monotonic()
    timed_out = False
    cancelled = progress.stop_requested()
    exit_code = 130 if cancelled else -1
    if cancelled:
        stdout_path.touch()
        atomic_text(stderr_path, "run-scoped STOP requested before launch\n")
    else:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                cwd=path.parent,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if progress.stop_requested():
                    cancelled = True
                    proof_runner.terminate_process_group(process)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    proof_runner.terminate_process_group(process)
                    break
                time.sleep(0.1)
            exit_code = (
                130
                if cancelled
                else 124
                if timed_out
                else int(process.returncode)
            )
        if cancelled:
            with stderr_path.open("a", encoding="utf-8") as stream:
                stream.write("\nrun-scoped STOP requested; process group terminated\n")
        elif timed_out:
            with stderr_path.open("a", encoding="utf-8") as stream:
                stream.write(f"\nmutation command timed out after {timeout} seconds\n")
    atomic_text(rc_path, f"{exit_code}\n")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    parsed_match = VERIFICATION_RE.search(stdout_text + "\n" + stderr_text)
    parsed = {
        "verified": int(parsed_match.group(1)) if parsed_match else None,
        "errors": int(parsed_match.group(2)) if parsed_match else None,
    }
    expected_observed = (
        not timed_out
        and not cancelled
        and (
            exit_code == 0
            if mode == "no_verify"
            else exit_code != 0
            and any(
                message in (stdout_text + stderr_text)
                for message in EXPECTED_REJECTION
            )
        )
    )
    status = (
        "cancelled"
        if cancelled
        else "passed"
        if expected_observed
        else "failed"
    )
    result = {
        "schema_version": 1,
        "run_id": progress.run_id,
        "row_id": row["row_id"],
        "target": row["target"],
        "proof_kind": proof_kind,
        "mutation_id": mutation_id_value,
        "mode": mode,
        "phase": phase,
        "status": status,
        "path": str(path.relative_to(progress.run_dir)),
        "sha256": sha256(path),
        "command": command,
        "command_text": (
            f"VERUS_Z3_PATH={z3} " + " ".join(command)
        ),
        "working_directory": str(path.parent),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "cancelled": cancelled,
        "duration_seconds": time.monotonic() - started,
        "parsed_verification": parsed,
        "command_path": str(command_path.relative_to(ROOT)),
        "command_sha256": sha256(command_path),
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stdout_sha256": sha256(stdout_path),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "stderr_sha256": sha256(stderr_path),
        "rc_path": str(rc_path.relative_to(ROOT)),
        "rc_sha256": sha256(rc_path),
        "expected_result_observed": expected_observed,
    }
    atomic_json(result_path, result)
    progress.finish(status)
    progress.event(
        "mutation_finished",
        row_id=row["row_id"],
        target=row["target"],
        phase=phase,
        status=status,
        exit_code=exit_code,
    )
    return {
        **result,
        "result_path": str(result_path.relative_to(ROOT)),
        "result_sha256": sha256(result_path),
    }


def run_probe(
    progress: Progress,
    *,
    snapshot: Path,
    row: dict[str, Any],
    proof_kind: str,
    mutation_id_value: str,
    plan: dict[str, Any],
    manifest_sha256: str,
    verus: Path,
    z3: Path,
    timeout: int,
) -> dict[str, Any]:
    path, baseline_hash, plan_hash = create_mutation(
        snapshot,
        row,
        proof_kind,
        mutation_id_value,
        plan,
    )
    evidence = (
        progress.run_dir
        / "targets"
        / proof_runner.target_evidence_name(row)
        / proof_kind
        / mutation_id_value
    )
    no_verify = run_command(
        progress,
        row=row,
        proof_kind=proof_kind,
        mutation_id_value=mutation_id_value,
        mode="no_verify",
        path=path,
        evidence_dir=evidence,
        verus=verus,
        z3=z3,
        timeout=timeout,
    )
    actual = run_command(
        progress,
        row=row,
        proof_kind=proof_kind,
        mutation_id_value=mutation_id_value,
        mode="actual",
        path=path,
        evidence_dir=evidence,
        verus=verus,
        z3=z3,
        timeout=timeout,
    )
    record_path = evidence / "probe.json"
    record = {
        "schema_version": 1,
        "run_id": progress.run_id,
        "row_id": row["row_id"],
        "target": row["target"],
        "proof_family": row.get("proof_family"),
        "proof_kind": proof_kind,
        "mutation_id": mutation_id_value,
        "category": plan.get("category"),
        "omitted_observable": plan.get("omitted_observable"),
        "baseline_fragment": plan.get("fragment"),
        "replacement": plan.get("replacement"),
        "plan_sha256": plan_hash,
        "proof_manifest_sha256": manifest_sha256,
        "baseline_proof_sha256": baseline_hash,
        "mutated_path": str(path.relative_to(progress.run_dir)),
        "mutated_sha256": sha256(path),
        "syntax_valid": (
            no_verify["status"] == "passed"
            and no_verify["exit_code"] == 0
        ),
        "actual_verus_rejected": (
            actual["status"] == "passed"
            and actual["exit_code"] != 0
        ),
        "results": [
            {
                "mode": result["mode"],
                "path": result["result_path"],
                "sha256": result["result_sha256"],
            }
            for result in (no_verify, actual)
        ],
    }
    atomic_json(record_path, record)
    return {
        **record,
        "record_path": str(record_path.relative_to(ROOT)),
        "record_sha256": sha256(record_path),
    }


def record_worker_failure(
    progress: Progress,
    row: dict[str, Any],
    proof_kind: str,
    mutation_id_value: str,
    plan: dict[str, Any],
    error: Exception,
) -> dict[str, Any]:
    record_path = (
        progress.run_dir
        / "targets"
        / proof_runner.target_evidence_name(row)
        / proof_kind
        / mutation_id_value
        / "probe.json"
    )
    record = {
        "schema_version": 1,
        "run_id": progress.run_id,
        "row_id": row["row_id"],
        "target": row["target"],
        "proof_family": row.get("proof_family"),
        "proof_kind": proof_kind,
        "mutation_id": mutation_id_value,
        "category": plan.get("category"),
        "omitted_observable": plan.get("omitted_observable"),
        "syntax_valid": False,
        "actual_verus_rejected": False,
        "worker_error": f"{type(error).__name__}: {error}",
        "results": [],
    }
    atomic_json(record_path, record)
    completed_results = sum(
        (
            record_path.parent
            / f"{proof_kind}_{mode}.json"
        ).is_file()
        for mode in ("no_verify", "actual")
    )
    for _ in range(2 - completed_results):
        progress.finish("failed")
    progress.event(
        "mutation_worker_failed",
        row_id=row["row_id"],
        target=row["target"],
        proof_kind=proof_kind,
        mutation_id=mutation_id_value,
        error=record["worker_error"],
    )
    return {
        **record,
        "record_path": str(record_path.relative_to(ROOT)),
        "record_sha256": sha256(record_path),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--target-row-id", action="append")
    parser.add_argument(
        "--representative",
        action="store_true",
        help="Diagnostic only: run one row per proof-family/category pair.",
    )
    parser.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    parser.add_argument("--z3", type=Path, default=DEFAULT_Z3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not proof_runner.valid_run_id(args.run_id):
        raise SystemExit(
            "run id must contain only letters, digits, dot, dash, or underscore"
        )
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    verus = args.verus.resolve()
    z3 = args.z3.resolve()
    if not verus.is_file() or not z3.is_file():
        raise FileNotFoundError(f"missing Verus or Z3: {verus}, {z3}")
    payload = load(TARGETS)
    all_rows = sorted(payload["rows"], key=lambda row: row["row_id"])
    proof_runner.validate_inventory(all_rows)
    rows = list(all_rows)
    if args.target_row_id:
        selected = set(args.target_row_id)
        rows = [row for row in rows if row["row_id"] in selected]
        if {row["row_id"] for row in rows} != selected:
            raise ValueError("one or more --target-row-id values are absent")
    probes: list[
        tuple[dict[str, Any], str, str, dict[str, Any], str]
    ] = []
    seen: set[tuple[str, str, str]] = set()
    for row in rows:
        manifest_path = target_dir(row) / "proof_manifest.json"
        manifest = load(manifest_path)
        for proof_kind in ("implementation", "completeness"):
            plans = mutation_plans(manifest, proof_kind)
            if not plans:
                raise ValueError(
                    f"{row['row_id']} has no {proof_kind} mutation plan"
                )
            ids = [
                mutation_id(plan, index, len(plans))
                for index, plan in enumerate(plans)
            ]
            if len(ids) != len(set(ids)):
                raise ValueError(
                    f"{row['row_id']} has duplicate {proof_kind} mutation ids"
                )
            for mutation_id_value, plan in zip(ids, plans):
                key = (
                    str(row.get("proof_family")),
                    str(plan.get("category")),
                    proof_kind,
                )
                if args.representative and key in seen:
                    continue
                seen.add(key)
                probes.append(
                    (
                        row,
                        proof_kind,
                        mutation_id_value,
                        plan,
                        sha256(manifest_path),
                    )
                )
    complete_campaign_run = (
        not args.target_row_id and not args.representative
    )
    if complete_campaign_run:
        for stale in (
            MUTATION_ROOT / "summary.json",
            MUTATION_ROOT / "latest.json",
        ):
            if stale.exists():
                stale.unlink()
        for row in rows:
            for proof_kind in ("implementation", "completeness"):
                pointer = (
                    target_dir(row)
                    / "evidence"
                    / "mutations"
                    / f"{proof_kind}.json"
                )
                if pointer.exists():
                    pointer.unlink()
    run_dir = proof_runner.checked_descendant(
        MUTATION_ROOT / "runs" / args.run_id,
        MUTATION_ROOT / "runs",
        "mutation run directory",
    )
    progress = Progress(args.run_id, run_dir, len(probes) * 2)
    snapshot, input_manifest = proof_runner.build_input_snapshot(rows, run_dir)
    versions = {
        "verus": proof_runner.version_output([str(verus), "--version"]),
        "z3": proof_runner.version_output([str(z3), "--version"]),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
    }
    atomic_json(run_dir / "versions.json", versions)
    manifest = {
        "schema_version": 2,
        "run_id": args.run_id,
        "representative": args.representative,
        "complete_campaign_run": complete_campaign_run,
        "probe_count": len(probes),
        "command_count": len(probes) * 2,
        "inventory_sha256": sha256(LIVE_INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "input_manifest_sha256": sha256(run_dir / "input_manifest.json"),
        "versions_sha256": sha256(run_dir / "versions.json"),
        "verus_path": str(verus),
        "z3_path": str(z3),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
        "expected_probes": [
            {
                "row_id": row["row_id"],
                "proof_kind": proof_kind,
                "mutation_id": mutation_id_value,
                "proof_manifest_sha256": manifest_hash,
                "plan_sha256": compact_hash(plan),
            }
            for (
                row,
                proof_kind,
                mutation_id_value,
                plan,
                manifest_hash,
            ) in probes
        ],
    }
    atomic_json(run_dir / "manifest.json", manifest)
    progress.event("run_started", manifest=manifest)
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_probe,
                progress,
                snapshot=snapshot,
                row=row,
                proof_kind=proof_kind,
                mutation_id_value=mutation_id_value,
                plan=plan,
                manifest_sha256=manifest_hash,
                verus=verus,
                z3=z3,
                timeout=args.timeout,
            ): (row, proof_kind, mutation_id_value, plan)
            for (
                row,
                proof_kind,
                mutation_id_value,
                plan,
                manifest_hash,
            ) in probes
        }
        for future in as_completed(futures):
            row, proof_kind, mutation_id_value, plan = futures[future]
            try:
                records.append(future.result())
            except Exception as error:
                records.append(
                    record_worker_failure(
                        progress,
                        row,
                        proof_kind,
                        mutation_id_value,
                        plan,
                        error,
                    )
                )
    records.sort(
        key=lambda record: (
            record["row_id"],
            record["proof_kind"],
            record["mutation_id"],
        )
    )
    passed = all(
        record["syntax_valid"] and record["actual_verus_rejected"]
        for record in records
    )
    status = (
        "cancelled"
        if progress.cancelled and not progress.failed
        else "passed"
        if passed
        else "failed"
    )
    result_index = [
        {
            "row_id": record["row_id"],
            "proof_kind": record["proof_kind"],
            "mutation_id": record["mutation_id"],
            "path": record["record_path"],
            "sha256": record["record_sha256"],
        }
        for record in records
    ]
    summary = {
        "schema_version": 2,
        "run_id": args.run_id,
        "status": status,
        "representative": args.representative,
        "complete_campaign_run": complete_campaign_run,
        "probe_count": len(records),
        "covered_categories": sorted(
            {str(record["category"]) for record in records}
        ),
        "proof_family_count": len(
            {str(record["proof_family"]) for record in records}
        ),
        "syntax_valid_count": sum(
            record["syntax_valid"] for record in records
        ),
        "actual_verus_rejected_count": sum(
            record["actual_verus_rejected"] for record in records
        ),
        "inventory_sha256": sha256(LIVE_INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "input_manifest_sha256": sha256(run_dir / "input_manifest.json"),
        "versions_sha256": sha256(run_dir / "versions.json"),
        "result_index": result_index,
        "result_index_sha256": compact_hash(result_index),
    }
    atomic_json(run_dir / "result.json", summary)
    atomic_json(
        run_dir / "status.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "state": status,
            "total_commands": len(probes) * 2,
            "completed_commands": progress.completed,
            "failed_commands": progress.failed,
            "cancelled_commands": progress.cancelled,
            "updated_at_utc": now(),
        },
    )
    progress.event("run_completed", summary=summary)
    if complete_campaign_run:
        atomic_json(MUTATION_ROOT / "summary.json", summary)
        if status == "passed":
            records_by_key: dict[
                tuple[str, str], list[dict[str, Any]]
            ] = {}
            for record in records:
                key = (record["row_id"], record["proof_kind"])
                records_by_key.setdefault(key, []).append(record)
            for row in rows:
                for proof_kind in ("implementation", "completeness"):
                    pointer_records = [
                        {
                            "mutation_id": record["mutation_id"],
                            "record_path": record["record_path"],
                            "record_sha256": record["record_sha256"],
                        }
                        for record in records_by_key[
                            (row["row_id"], proof_kind)
                        ]
                    ]
                    atomic_json(
                        target_dir(row)
                        / "evidence"
                        / "mutations"
                        / f"{proof_kind}.json",
                        {
                            "schema_version": 2,
                            "authoritative": False,
                            "run_id": args.run_id,
                            "row_id": row["row_id"],
                            "target": row["target"],
                            "proof_kind": proof_kind,
                            "records": pointer_records,
                        },
                    )
            atomic_json(
                MUTATION_ROOT / "latest.json",
                {
                    "schema_version": 2,
                    "run_id": args.run_id,
                    "run_dir": str(run_dir.relative_to(ROOT)),
                    "result_sha256": sha256(run_dir / "result.json"),
                    "manifest_sha256": sha256(run_dir / "manifest.json"),
                    "input_manifest_sha256": sha256(
                        run_dir / "input_manifest.json"
                    ),
                    "versions_sha256": sha256(run_dir / "versions.json"),
                },
            )
    print(json.dumps(summary, sort_keys=True))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
