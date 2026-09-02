#!/usr/bin/env python3
"""Run both Verus modes over immutable, retained core::cmp proof inputs."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import threading
import time
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
LIVE_INVENTORY = ROOT / "inventory" / "core_cmp_exec_fn_inventory.json"
SPECIFICATION_CATALOG = ROOT / "specs" / "all_cmp_specs.json"
TARGETS = ROOT / "proof_inventory" / "targets.json"
SPECIFICATION_REVIEW = ROOT / "reviews" / "independent_specification_review.json"
EVIDENCE_BASE = ROOT / "verification" / "evidence"
EVIDENCE_ROOT = EVIDENCE_BASE / "implementation-proofs"
DEFAULT_VERUS = (
    ROOT.parent / "verus" / "source" / "target-verus" / "release" / "verus"
)
DEFAULT_Z3 = ROOT.parent / "verus" / "source" / "z3"
VERIFICATION_RE = re.compile(
    r"verification results::\s*(\d+)\s+verified,\s*(\d+)\s+errors"
)
INCLUDE_RE = re.compile(r'include!\(\s*"([^"]+)"\s*\)')
MODULE_RE = re.compile(
    r"(?m)^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+([A-Za-z0-9_]+)\s*;"
)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def checked_descendant(path: Path, parent: Path, label: str) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(parent.resolve())
    except ValueError as error:
        raise ValueError(f"{label} escapes {parent}: {path}") from error
    return resolved


def valid_run_id(value: str) -> bool:
    return bool(value) and all(
        character.isalnum() or character in "._-" for character in value
    )


def target_dir(row: dict[str, Any]) -> Path:
    relative = (
        row.get("target_dir")
        or row.get("harness_dir")
        or f"proof_harnesses/{row['slug']}"
    )
    return checked_descendant(
        ROOT / str(relative),
        ROOT / "proof_harnesses",
        "target directory",
    )


def target_evidence_name(row: dict[str, Any]) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(row["row_id"]))


def validate_inventory(rows: list[dict[str, Any]]) -> None:
    live = load(LIVE_INVENTORY)["rows"]
    selected_ids = {
        row["row_id"]
        for row in load(SPECIFICATION_CATALOG)["rows"]
        if row["disposition"] in {"generated", "exact_vstd"}
    }
    live_ids = [
        row["row_id"] for row in live if row["row_id"] in selected_ids
    ]
    proof_ids = [row["row_id"] for row in rows]
    if len(proof_ids) != len(set(proof_ids)):
        raise ValueError("proof inventory contains duplicate row ids")
    if set(proof_ids) != set(live_ids):
        missing = sorted(set(live_ids) - set(proof_ids))
        extra = sorted(set(proof_ids) - set(live_ids))
        raise ValueError(
            f"proof inventory identity mismatch: missing={missing} extra={extra}"
        )
    directories = [target_dir(row) for row in rows]
    if len(directories) != len(set(directories)):
        raise ValueError("proof inventory reuses a target directory")
    for row in rows:
        directory = target_dir(row)
        for name in (
            "implementation_proof.rs",
            "completeness_proof.rs",
            "proof_manifest.json",
        ):
            if not (directory / name).is_file():
                raise FileNotFoundError(f"missing {directory / name}")


def source_dependencies(path: Path, seen: set[Path]) -> None:
    path = checked_descendant(path, ROOT, "verifier input")
    if path in seen:
        return
    if not path.is_file():
        raise FileNotFoundError(f"verifier input is missing: {path}")
    seen.add(path)
    if path.suffix != ".rs":
        return
    text = path.read_text(encoding="utf-8")
    for relative in INCLUDE_RE.findall(text):
        source_dependencies(path.parent / relative, seen)
    for module in MODULE_RE.findall(text):
        flat = path.parent / f"{module}.rs"
        nested = path.parent / module / "mod.rs"
        if flat.is_file():
            source_dependencies(flat, seen)
        elif nested.is_file():
            source_dependencies(nested, seen)


def verifier_input_closure(
    row: dict[str, Any],
    proof_kind: str,
) -> list[Path]:
    directory = target_dir(row)
    metadata = {
        path.resolve()
        for path in directory.rglob("*")
        if path.is_file()
        and (path.suffix == ".json" or path.name.endswith(".toml"))
        and "evidence" not in path.parts
        and not path.name.endswith("_mutation_evidence.json")
        and path.name != "verification_manifest.json"
    }
    closure: set[Path] = set(metadata)
    source_dependencies(
        directory / f"{proof_kind}_proof.rs",
        closure,
    )
    return sorted(
        closure,
        key=lambda path: str(path.relative_to(ROOT)),
    )


def build_input_snapshot(
    rows: list[dict[str, Any]],
    run_dir: Path,
) -> tuple[Path, dict[str, Any]]:
    snapshot = run_dir / "input_snapshot"
    closure_records: list[dict[str, Any]] = []
    all_inputs: set[Path] = set()
    for row in rows:
        directory = target_dir(row)
        for proof_kind in ("implementation", "completeness"):
            proof = directory / f"{proof_kind}_proof.rs"
            ordered = verifier_input_closure(row, proof_kind)
            all_inputs.update(ordered)
            inputs = [
                {
                    "path": str(path.relative_to(ROOT)),
                    "sha256": sha256(path),
                    "size": path.stat().st_size,
                }
                for path in ordered
            ]
            closure_records.append(
                {
                    "row_id": row["row_id"],
                    "target": row["target"],
                    "proof_kind": proof_kind,
                    "proof_path": str(proof.relative_to(ROOT)),
                    "inputs": inputs,
                    "closure_sha256": compact_hash(inputs),
                }
            )
    for source in sorted(
        all_inputs,
        key=lambda path: str(path.relative_to(ROOT)),
    ):
        destination = snapshot / source.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        destination.chmod(0o444)
    manifest = {
        "schema_version": 1,
        "campaign_root": str(ROOT),
        "snapshot_root": str(snapshot),
        "inventory_sha256": sha256(LIVE_INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "specification_review_sha256": sha256(SPECIFICATION_REVIEW),
        "unique_input_count": len(all_inputs),
        "closures": closure_records,
    }
    atomic_json(run_dir / "input_manifest.json", manifest)
    return snapshot, manifest


def closure_by_key(manifest: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (record["row_id"], record["proof_kind"]): record
        for record in manifest["closures"]
    }


def command_text(command: list[str], z3: Path) -> str:
    return f"VERUS_Z3_PATH={z3} " + " ".join(command)


def parse_verification(stdout: str, stderr: str) -> dict[str, int | None]:
    match = VERIFICATION_RE.search(stdout + "\n" + stderr)
    if match is None:
        return {"verified": None, "errors": None}
    return {
        "verified": int(match.group(1)),
        "errors": int(match.group(2)),
    }


class Run:
    def __init__(
        self,
        run_id: str,
        run_dir: Path,
        total_commands: int,
    ) -> None:
        self.run_id = run_id
        self.run_dir = run_dir
        self.total_commands = total_commands
        self.completed = 0
        self.failed = 0
        self.cancelled_commands = 0
        self.lock = threading.Lock()
        self.started_at = now()
        self.progress = run_dir / "progress.jsonl"
        run_dir.mkdir(parents=True, exist_ok=False)
        self.progress.touch()

    def stop_requested(self) -> bool:
        return (self.run_dir / "STOP").exists()

    def event(self, event: str, **details: Any) -> None:
        record = {
            "event": event,
            "run_id": self.run_id,
            "timestamp_utc": now(),
            **details,
        }
        with self.lock:
            with self.progress.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, sort_keys=True) + "\n")
                stream.flush()
                os.fsync(stream.fileno())

    def finish_command(self, status: str) -> None:
        with self.lock:
            self.completed += 1
            if status == "failed":
                self.failed += 1
            elif status == "cancelled":
                self.cancelled_commands += 1
            atomic_json(
                self.run_dir / "status.json",
                {
                    "schema_version": 1,
                    "run_id": self.run_id,
                    "state": "running",
                    "started_at_utc": self.started_at,
                    "updated_at_utc": now(),
                    "total_commands": self.total_commands,
                    "completed_commands": self.completed,
                    "failed_commands": self.failed,
                    "cancelled_commands": self.cancelled_commands,
                },
            )


def terminate_process_group(process: subprocess.Popen[Any]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            pass


def run_one(
    run: Run,
    *,
    row: dict[str, Any],
    proof_kind: str,
    mode: str,
    snapshot: Path,
    closure: dict[str, Any],
    verus: Path,
    z3: Path,
    timeout: int,
) -> dict[str, Any]:
    source_directory = target_dir(row)
    source_proof = source_directory / f"{proof_kind}_proof.rs"
    proof = snapshot / source_proof.relative_to(ROOT)
    proof = checked_descendant(proof, snapshot, "snapshot proof")
    phase = f"{proof_kind}_{mode}"
    evidence_dir = (
        run.run_dir / "targets" / target_evidence_name(row) / phase
    )
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = evidence_dir / "stdout.txt"
    stderr_path = evidence_dir / "stderr.txt"
    command_path = evidence_dir / "command.txt"
    rc_path = evidence_dir / "rc.txt"
    result_path = evidence_dir / "result.json"
    command = [str(verus), str(proof), "--crate-type=lib"]
    if mode == "no_verify":
        command.append("--no-verify")
    atomic_text(command_path, command_text(command, z3) + "\n")
    started_at = now()
    started = time.monotonic()
    run.event(
        "proof_started",
        row_id=row["row_id"],
        target=row["target"],
        phase=phase,
        snapshot_proof=str(proof.relative_to(run.run_dir)),
    )
    timed_out = False
    cancelled = run.stop_requested()
    exit_code = 130 if cancelled else -1
    environment = os.environ.copy()
    environment["VERUS_Z3_PATH"] = str(z3)
    if cancelled:
        stdout_path.touch()
        atomic_text(stderr_path, "run-scoped STOP requested before launch\n")
    else:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(
                command,
                cwd=proof.parent,
                env=environment,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
            )
            deadline = time.monotonic() + timeout
            while process.poll() is None:
                if run.stop_requested():
                    cancelled = True
                    terminate_process_group(process)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    terminate_process_group(process)
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
                stream.write(f"\nproof command timed out after {timeout} seconds\n")
    atomic_text(rc_path, f"{exit_code}\n")
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")
    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace")
    parsed = parse_verification(stdout_text, stderr_text)
    snapshot_hash = sha256(proof)
    expected_proof_hash = next(
        record["sha256"]
        for record in closure["inputs"]
        if record["path"] == str(source_proof.relative_to(ROOT))
    )
    input_unchanged = all(
        sha256(snapshot / record["path"]) == record["sha256"]
        for record in closure["inputs"]
    )
    passed = (
        not cancelled
        and not timed_out
        and exit_code == 0
        and input_unchanged
        and (
            mode == "no_verify"
            or (
                parsed["errors"] == 0
                and isinstance(parsed["verified"], int)
                and parsed["verified"] >= 1
            )
        )
    )
    status = "cancelled" if cancelled else "passed" if passed else "failed"
    result = {
        "schema_version": 1,
        "run_id": run.run_id,
        "row_id": row["row_id"],
        "target": row["target"],
        "phase": phase,
        "proof_kind": proof_kind,
        "mode": mode,
        "status": status,
        "command": command,
        "command_text": command_text(command, z3),
        "working_directory": str(proof.parent),
        "source_proof_path": str(source_proof.relative_to(ROOT)),
        "snapshot_proof_path": str(proof.relative_to(run.run_dir)),
        "proof_sha256": snapshot_hash,
        "expected_proof_sha256": expected_proof_hash,
        "input_closure_sha256": closure["closure_sha256"],
        "inventory_sha256": sha256(LIVE_INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "specification_review_sha256": sha256(SPECIFICATION_REVIEW),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
        "started_at_utc": started_at,
        "completed_at_utc": now(),
        "duration_seconds": time.monotonic() - started,
        "exit_code": exit_code,
        "timed_out": timed_out,
        "cancelled": cancelled,
        "input_unchanged": input_unchanged,
        "parsed_verification": parsed,
        "command_path": str(command_path.relative_to(ROOT)),
        "command_sha256": sha256(command_path),
        "stdout_path": str(stdout_path.relative_to(ROOT)),
        "stdout_sha256": sha256(stdout_path),
        "stderr_path": str(stderr_path.relative_to(ROOT)),
        "stderr_sha256": sha256(stderr_path),
        "rc_path": str(rc_path.relative_to(ROOT)),
        "rc_sha256": sha256(rc_path),
    }
    atomic_json(result_path, result)
    run.finish_command(status)
    run.event(
        "proof_finished",
        row_id=row["row_id"],
        target=row["target"],
        phase=phase,
        status=status,
        exit_code=exit_code,
        duration_seconds=result["duration_seconds"],
    )
    return {
        **result,
        "result_path": str(result_path.relative_to(ROOT)),
        "result_sha256": sha256(result_path),
    }


def record_worker_failure(
    run: Run,
    row: dict[str, Any],
    proof_kind: str,
    mode: str,
    error: Exception,
) -> dict[str, Any]:
    phase = f"{proof_kind}_{mode}"
    result_path = (
        run.run_dir
        / "targets"
        / target_evidence_name(row)
        / phase
        / "result.json"
    )
    result = {
        "schema_version": 1,
        "run_id": run.run_id,
        "row_id": row["row_id"],
        "target": row["target"],
        "phase": phase,
        "proof_kind": proof_kind,
        "mode": mode,
        "status": "failed",
        "exit_code": -1,
        "timed_out": False,
        "cancelled": False,
        "worker_error": f"{type(error).__name__}: {error}",
    }
    atomic_json(result_path, result)
    run.finish_command("failed")
    run.event(
        "proof_worker_failed",
        row_id=row["row_id"],
        target=row["target"],
        phase=phase,
        error=result["worker_error"],
    )
    return {
        **result,
        "result_path": str(result_path.relative_to(ROOT)),
        "result_sha256": sha256(result_path),
    }


def version_output(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return {
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument(
        "--phase",
        choices=("all", "no-verify", "actual"),
        default="all",
    )
    parser.add_argument("--target-row-id", action="append")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--verus", type=Path, default=DEFAULT_VERUS)
    parser.add_argument("--z3", type=Path, default=DEFAULT_Z3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not valid_run_id(args.run_id):
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
    all_rows = payload["rows"]
    validate_inventory(all_rows)
    rows = list(all_rows)
    if args.target_row_id:
        selected = set(args.target_row_id)
        rows = [row for row in rows if row["row_id"] in selected]
        if {row["row_id"] for row in rows} != selected:
            raise ValueError("one or more --target-row-id values are absent")
    rows = sorted(rows, key=lambda row: row["row_id"])
    modes = (
        ("no_verify", "actual")
        if args.phase == "all"
        else (args.phase.replace("-", "_"),)
    )
    tasks = [
        (row, proof_kind, mode)
        for row in rows
        for proof_kind in ("implementation", "completeness")
        for mode in modes
    ]
    requested_run_dir = (
        args.run_dir
        if args.run_dir
        else EVIDENCE_ROOT / args.run_id
    )
    if not requested_run_dir.is_absolute():
        requested_run_dir = ROOT / requested_run_dir
    run_dir = checked_descendant(
        requested_run_dir,
        EVIDENCE_BASE,
        "proof run directory",
    )
    run = Run(args.run_id, run_dir, len(tasks))
    snapshot, input_manifest = build_input_snapshot(rows, run_dir)
    closures = closure_by_key(input_manifest)
    versions = {
        "verus": version_output([str(verus), "--version"]),
        "z3": version_output([str(z3), "--version"]),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
    }
    atomic_json(run_dir / "versions.json", versions)
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "phase": args.phase,
        "complete_campaign_run": (
            not args.target_row_id and args.phase == "all"
        ),
        "target_count": len(rows),
        "command_count": len(tasks),
        "workers": args.workers,
        "timeout_seconds": args.timeout,
        "inventory_sha256": sha256(LIVE_INVENTORY),
        "proof_inventory_sha256": sha256(TARGETS),
        "specification_review_sha256": sha256(SPECIFICATION_REVIEW),
        "input_manifest_sha256": sha256(run_dir / "input_manifest.json"),
        "versions_sha256": sha256(run_dir / "versions.json"),
        "verus_path": str(verus),
        "z3_path": str(z3),
        "verus_binary_sha256": sha256(verus),
        "z3_sha256": sha256(z3),
        "target_row_ids": [row["row_id"] for row in rows],
    }
    atomic_json(run_dir / "manifest.json", manifest)
    run.event("run_started", manifest=manifest)
    atomic_json(
        run_dir / "status.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "state": "running",
            "started_at_utc": run.started_at,
            "updated_at_utc": now(),
            "total_commands": len(tasks),
            "completed_commands": 0,
            "failed_commands": 0,
            "cancelled_commands": 0,
        },
    )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_one,
                run,
                row=row,
                proof_kind=proof_kind,
                mode=mode,
                snapshot=snapshot,
                closure=closures[(row["row_id"], proof_kind)],
                verus=verus,
                z3=z3,
                timeout=args.timeout,
            ): (row, proof_kind, mode)
            for row, proof_kind, mode in tasks
        }
        for future in as_completed(futures):
            row, proof_kind, mode = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                results.append(
                    record_worker_failure(
                        run,
                        row,
                        proof_kind,
                        mode,
                        error,
                    )
                )
    results.sort(key=lambda result: (result["row_id"], result["phase"]))
    by_row: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_row.setdefault(result["row_id"], []).append(result)
    verified_rows = 0
    for row in rows:
        row_results = by_row[row["row_id"]]
        all_passed = len(row_results) == len(modes) * 2 and all(
            result["status"] == "passed" for result in row_results
        )
        if all_passed:
            verified_rows += 1
        pointer = {
            "schema_version": 1,
            "authoritative": False,
            "run_id": args.run_id,
            "row_id": row["row_id"],
            "target": row["target"],
            "status": "passed" if all_passed else "failed",
            "run_manifest": {
                "path": str((run_dir / "manifest.json").relative_to(ROOT)),
                "sha256": sha256(run_dir / "manifest.json"),
            },
            "command_records": [
                {
                    "phase": result["phase"],
                    "path": result["result_path"],
                    "sha256": result["result_sha256"],
                }
                for result in row_results
            ],
        }
        atomic_json(target_dir(row) / "verification_manifest.json", pointer)
        atomic_json(target_dir(row) / "evidence" / "latest.json", pointer)
    failed = [
        {
            "row_id": result["row_id"],
            "target": result["target"],
            "phase": result["phase"],
            "status": result["status"],
            "exit_code": result["exit_code"],
            "timed_out": result["timed_out"],
        }
        for result in results
        if result["status"] != "passed"
    ]
    status = "passed" if not failed else (
        "cancelled"
        if run.cancelled_commands and not run.failed
        else "failed"
    )
    result_index = [
        {
            "row_id": result["row_id"],
            "target": result["target"],
            "phase": result["phase"],
            "path": result["result_path"],
            "sha256": result["result_sha256"],
        }
        for result in results
    ]
    summary = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": status,
        "phase": args.phase,
        "complete_campaign_run": manifest["complete_campaign_run"],
        "target_count": len(rows),
        "verified_target_count": verified_rows,
        "command_count": len(results),
        "passed_command_count": sum(
            result["status"] == "passed" for result in results
        ),
        "failed_command_count": sum(
            result["status"] == "failed" for result in results
        ),
        "cancelled_command_count": sum(
            result["status"] == "cancelled" for result in results
        ),
        "failed_results": failed,
        "result_index": result_index,
        "result_index_sha256": compact_hash(result_index),
        "started_at_utc": run.started_at,
        "completed_at_utc": now(),
        "manifest_sha256": sha256(run_dir / "manifest.json"),
        "input_manifest_sha256": sha256(run_dir / "input_manifest.json"),
        "versions_sha256": sha256(run_dir / "versions.json"),
    }
    atomic_json(run_dir / "result.json", summary)
    atomic_json(
        run_dir / "status.json",
        {
            "schema_version": 1,
            "run_id": args.run_id,
            "state": status,
            "started_at_utc": run.started_at,
            "updated_at_utc": now(),
            "total_commands": len(tasks),
            "completed_commands": run.completed,
            "failed_commands": run.failed,
            "cancelled_commands": run.cancelled_commands,
        },
    )
    run.event("run_completed", summary=summary)
    if status == "passed" and manifest["complete_campaign_run"]:
        EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
        atomic_json(
            EVIDENCE_ROOT / "latest.json",
            {
                "schema_version": 1,
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
