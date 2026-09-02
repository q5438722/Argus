#!/usr/bin/env python3
"""Run and persist the complete BTreeSet two-mode Verus/mutation matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools import campaign_model, proof_model, verus_evidence


ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "inventory/btree_set_exec_fn_inventory.json"
VERUS = ROOT.parent / "verus/source/target-verus/release/verus"
Z3 = ROOT.parent / "verus/source/target-verus/release/z3"
EVIDENCE_ROOT = ROOT / "verification/evidence/verus_matrix"
POSITIVE_RESULT = re.compile(r"verification results::\s+\d+ verified, 0 errors")


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
        self.status("pending", None)

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
        self.append_jsonl(
            "progress.jsonl",
            {
                "timestamp": now(),
                "event": event,
                "run_id": self.run_id,
                "done": self.done,
                "total": self.total,
                "phase": "verus_matrix",
                **extra,
            },
        )

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


def invoke_verus(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except subprocess.TimeoutExpired as error:
        return subprocess.CompletedProcess(
            command,
            124,
            error.stdout or "",
            (error.stderr or "") + "\nTIMEOUT\n",
        )


def associated_item_air_limitation_matches(
    returncode: int,
    output: str,
) -> bool:
    return verus_evidence.associated_item_air_limitation_matches(
        returncode,
        output,
    )


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
    evidence_root.mkdir(parents=True, exist_ok=True)
    rendered = shlex.join(command)
    (evidence_root / f"{name}.command").write_text(rendered + "\n", encoding="utf-8")
    (evidence_root / f"{name}.stdout").write_text(result.stdout, encoding="utf-8")
    (evidence_root / f"{name}.stderr").write_text(result.stderr, encoding="utf-8")
    (evidence_root / f"{name}.rc").write_text(
        f"{result.returncode}\n", encoding="utf-8"
    )
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
    *,
    no_verify: bool,
    expected_mutation_failure: bool = False,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    command = command_for(path, no_verify)
    live.status("running", f"{target_id}/{trial_name}")
    live.event(
        "trial_started",
        target_id=target_id,
        trial=trial_name,
        command=shlex.join(command),
    )
    started = time.monotonic()
    result = invoke_verus(command)
    duration_ms = int((time.monotonic() - started) * 1000)
    combined = result.stdout + "\n" + result.stderr
    mutation_rejection_kind = None
    if expected_mutation_failure:
        mutation_rejection_kind = verus_evidence.mutation_rejection_kind(
            combined
        )
        passed = (
            result.returncode != 0
            and mutation_rejection_kind is not None
        )
        expectation = (
            "actual Verus rejects the type-correct source-step mutation "
            "by a semantic proof obligation"
        )
    elif no_verify:
        passed = result.returncode == 0
        expectation = "Verus --no-verify accepts exact syntax and types"
    else:
        passed = (
            result.returncode == 0 and POSITIVE_RESULT.search(combined) is not None
        )
        expectation = "actual Verus reports verified with zero errors"
    evidence = evidence_root or (path.parent / "evidence")
    record = write_evidence(
        evidence,
        trial_name,
        command,
        path,
        result,
        duration_ms,
        passed,
        expectation,
    )
    if expected_mutation_failure:
        record["mutation_rejection_kind"] = mutation_rejection_kind
        atomic_json(evidence / f"{trial_name}.json", record)
    live.log(result.stdout, result.stderr, f"{target_id}/{trial_name}")
    live.done += 1
    if not passed:
        live.failed += 1
    record.update({"target_id": target_id, "trial": trial_name})
    live.append_jsonl("run_results.jsonl", record)
    live.event(
        "trial_done" if passed else "trial_failed",
        target_id=target_id,
        trial=trial_name,
        passed=passed,
        returncode=result.returncode,
        duration_ms=duration_ms,
    )
    return record


def execute_associated_item_adjudication(
    live: LiveRun,
    target_id: str,
    trial_name: str,
    exact_source: Path,
    adjudication_source: Path,
    *,
    expected_mutation_failure: bool,
) -> dict[str, Any]:
    exact_command = command_for(exact_source, False)
    fallback_command = command_for(adjudication_source, False)
    live.status("running", f"{target_id}/{trial_name}")
    live.event(
        "trial_started",
        target_id=target_id,
        trial=trial_name,
        command=shlex.join(exact_command),
        checker_adjudication=(
            "verus-intoiterator-associated-item-air"
        ),
    )
    exact_started = time.monotonic()
    exact_result = invoke_verus(exact_command)
    exact_duration_ms = int(
        (time.monotonic() - exact_started) * 1000
    )
    exact_text = exact_result.stdout + "\n" + exact_result.stderr
    exact_limitation_matched = associated_item_air_limitation_matches(
        exact_result.returncode,
        exact_text,
    )

    fallback_started = time.monotonic()
    fallback_result = invoke_verus(fallback_command)
    fallback_duration_ms = int(
        (time.monotonic() - fallback_started) * 1000
    )
    fallback_text = (
        fallback_result.stdout + "\n" + fallback_result.stderr
    )
    fallback_rejection_kind = None
    if expected_mutation_failure:
        fallback_rejection_kind = (
            verus_evidence.mutation_rejection_kind(fallback_text)
        )
        fallback_passed = (
            fallback_result.returncode != 0
            and fallback_rejection_kind is not None
        )
        fallback_expectation = (
            "actual Verus rejects the stronger-domain source-step "
            "mutation by a semantic proof obligation"
        )
    else:
        fallback_passed = (
            fallback_result.returncode == 0
            and POSITIVE_RESULT.search(fallback_text) is not None
        )
        fallback_expectation = (
            "actual Verus verifies the same executable body after "
            "erasing only the crashing associated-item equality bound"
        )
    passed = exact_limitation_matched and fallback_passed
    evidence = exact_source.parent / "evidence"
    fallback_name = f"{trial_name}_checker_adjudication"
    fallback_record = write_evidence(
        evidence,
        fallback_name,
        fallback_command,
        adjudication_source,
        fallback_result,
        fallback_duration_ms,
        fallback_passed,
        fallback_expectation,
    )
    if expected_mutation_failure:
        fallback_record["mutation_rejection_kind"] = (
            fallback_rejection_kind
        )
        atomic_json(
            evidence / f"{fallback_name}.json",
            fallback_record,
        )
    record = write_evidence(
        evidence,
        trial_name,
        exact_command,
        exact_source,
        exact_result,
        exact_duration_ms,
        passed,
        (
            "exact mutation signature reproduces the narrowly matched "
            "Verus associated-item AIR failure and actual Verus rejects "
            "the stronger-domain mutation by a semantic proof obligation"
            if expected_mutation_failure
            else
            "exact signature reproduces the narrowly matched Verus "
            "associated-item AIR failure and the stronger bound-erased "
            "body discharges the same proof obligation"
        ),
    )
    record.update(
        {
            "result_kind": "checker_adjudicated",
            "checker_limitation": (
                "verus-intoiterator-associated-item-air"
            ),
            "exact_checker_failure_matched": exact_limitation_matched,
            "checker_adjudication_evidence": str(
                (
                    evidence / f"{fallback_name}.json"
                ).relative_to(ROOT)
            ),
            "checker_adjudication_source_sha256": fallback_record[
                "source_sha256"
            ],
            "checker_adjudication_passed": fallback_passed,
            "checker_adjudication_rejection_kind": (
                fallback_rejection_kind
                if expected_mutation_failure
                else None
            ),
        }
    )
    atomic_json(evidence / f"{trial_name}.json", record)
    live.log(
        exact_result.stdout,
        exact_result.stderr,
        f"{target_id}/{trial_name}/exact",
    )
    live.log(
        fallback_result.stdout,
        fallback_result.stderr,
        f"{target_id}/{trial_name}/checker_adjudication",
    )
    live.done += 1
    if not passed:
        live.failed += 1
    trial_record = {
        **record,
        "target_id": target_id,
        "trial": trial_name,
    }
    live.append_jsonl("run_results.jsonl", trial_record)
    live.event(
        "trial_done" if passed else "trial_failed",
        target_id=target_id,
        trial=trial_name,
        passed=passed,
        returncode=exact_result.returncode,
        fallback_returncode=fallback_result.returncode,
        duration_ms=exact_duration_ms + fallback_duration_ms,
    )
    return trial_record


def reuse_trial(
    live: LiveRun,
    base_run_id: str,
    target_id: str,
    trial_name: str,
    source: Path,
    evidence_root: Path,
) -> dict[str, Any]:
    record_path = evidence_root / f"{trial_name}.json"
    if not record_path.is_file():
        raise RuntimeError(
            f"missing reusable evidence record: {record_path}"
        )
    record = json.loads(record_path.read_text(encoding="utf-8"))
    source_sha256 = sha256_file(source)
    if (
        record.get("passed") is not True
        or record.get("source_sha256") != source_sha256
    ):
        raise RuntimeError(
            f"stale reusable evidence for {target_id}/{trial_name}"
        )
    reused = {
        **record,
        "target_id": target_id,
        "trial": trial_name,
        "reused_from_run_id": base_run_id,
        "reused_evidence": str(record_path.relative_to(ROOT)),
    }
    live.done += 1
    live.append_jsonl("run_results.jsonl", reused)
    live.event(
        "trial_reused",
        target_id=target_id,
        trial=trial_name,
        source_sha256=source_sha256,
        base_run_id=base_run_id,
    )
    return reused


def copy_module_evidence(base_run_id: str, destination: Path) -> None:
    source = EVIDENCE_ROOT / base_run_id / "module_evidence"
    if not source.is_dir():
        raise RuntimeError(f"missing base module evidence: {source}")
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        if path.is_file():
            shutil.copy2(path, destination / path.name)


def update_campaign(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    latest = {
        "schema_version": 1,
        "run_id": summary["run_id"],
        "summary": summary["summary_path"],
        "summary_sha256": sha256_file(ROOT / summary["summary_path"]),
        "completed_at": summary["completed_at"],
        "status": summary["status"],
    }
    atomic_json(EVIDENCE_ROOT / "latest_manifest.json", latest)
    total = len(rows)
    live_rows = campaign_model.derive_inventory(
        campaign_model.load_rustdoc()
    )[0]
    literal_external_body_counts = (
        proof_model.aggregate_literal_external_body_counts(live_rows)
    )
    lower_external_bodies = literal_external_body_counts["harness"]
    passed = summary["status"] == "passed"
    for name, payload in {
        "proof_evidence_audit.json": {
            "status": "passed" if passed else "failed",
            "checked_targets": total,
            "implementation_actual_verus_verified": summary[
                "implementation_actual_verus_verified"
            ],
            "implementation_actual_verus_native_verified": summary[
                "implementation_actual_verus_native_verified"
            ],
            "implementation_actual_verus_checker_adjudicated": summary[
                "implementation_actual_verus_checker_adjudicated"
            ],
            "completeness_actual_verus_verified": summary[
                "completeness_actual_verus_verified"
            ],
        },
        "mutation_audit.json": {
            "status": "passed" if passed else "failed",
            "expected_rejections": total,
            "observed_rejections": summary["mutations_rejected"],
            "native_rejections": summary["mutations_native_rejected"],
            "checker_adjudicated_rejections": summary[
                "mutations_checker_adjudicated"
            ],
        },
    }.items():
        atomic_json(
            ROOT / "verification/audits" / name,
            {
                "schema_version": 1,
                "module": "alloc::collections::btree_set",
                **payload,
            },
        )
    aggregate_path = ROOT / "proof_inventory/aggregate_coverage.json"
    aggregate = json.loads(aggregate_path.read_text(encoding="utf-8"))
    aggregate.update(
        {
            "actual_verus_verified": summary[
                "implementation_actual_verus_verified"
            ],
            "actual_verus_native_verified": summary[
                "implementation_actual_verus_native_verified"
            ],
            "actual_verus_checker_adjudicated": summary[
                "implementation_actual_verus_checker_adjudicated"
            ],
            "completeness_verified": summary[
                "completeness_actual_verus_verified"
            ],
            "mutation_rejected": summary["mutations_rejected"],
            "mutation_native_rejected": summary[
                "mutations_native_rejected"
            ],
            "mutation_checker_adjudicated": summary[
                "mutations_checker_adjudicated"
            ],
            "failed": summary["failed_targets"],
            "pending": (
                total - summary["passed_targets"]
                if not passed
                else 0
            ),
            "evidence_status": (
                "verus_matrix_passed_feedback_current"
                if passed
                else "verus_matrix_failed"
            ),
            "harness_literal_external_body_occurrences": lower_external_bodies,
            "target_external_body": literal_external_body_counts["target"],
            "target_external_body_occurrences": (
                literal_external_body_counts["target"]
            ),
            "completeness_external_body_occurrences": (
                literal_external_body_counts["completeness"]
            ),
            "dependency_external_body_occurrences": (
                literal_external_body_counts["dependency"]
            ),
            "helper_external_body_occurrences": (
                literal_external_body_counts["helper"]
            ),
            "literal_external_body_occurrences_by_category": (
                literal_external_body_counts
            ),
            "shared_vocabulary_external_body_occurrences_per_harness": (
                campaign_model.SHARED_VOCABULARY.count(
                    "#[verifier::external_body]"
                )
            ),
            "compiled_harness_external_body_occurrences": (
                lower_external_bodies
                + total
                * campaign_model.SHARED_VOCABULARY.count(
                    "#[verifier::external_body]"
                )
            ),
            "whole_contract_dependency": 0,
        }
    )
    atomic_json(aggregate_path, aggregate)
    counts = json.loads(INVENTORY.read_text(encoding="utf-8"))["counts"]
    (ROOT / "proof_inventory/aggregate_coverage.md").write_text(
        f"""# BTreeSet implementation/completeness aggregate

- Stable inventory rows: {total}
- Selected targets: {total}
- Generated contracts: {counts['generated']}
- Exact-vstd contracts: {counts['exact_vstd']}
- Actual Verus: {summary['implementation_actual_verus_verified']}
- Native exact-signature actual Verus: {summary['implementation_actual_verus_native_verified']}
- Associated-item checker adjudications: {summary['implementation_actual_verus_checker_adjudicated']}
- Exact-observation completeness: {summary['completeness_actual_verus_verified']}
- Mutation rejections: {summary['mutations_rejected']}
- Native exact-signature mutation rejections: {summary['mutations_native_rejected']}
- Stronger-domain adjudicated mutation rejections: {summary['mutations_checker_adjudicated']}
- Failed: {summary['failed_targets']}
- Pending: {aggregate['pending']}
- Target `external_body` occurrences: {literal_external_body_counts['target']}
- Completeness `external_body` occurrences:
  {literal_external_body_counts['completeness']}
- Lower dependency `external_body` occurrences:
  {literal_external_body_counts['dependency']}
- Local helper `external_body` occurrences:
  {literal_external_body_counts['helper']}
- Canonical harness literal `external_body` occurrences:
  {literal_external_body_counts['harness']}
- Included shared type-model `external_body` helpers per harness:
  {campaign_model.SHARED_VOCABULARY.count("#[verifier::external_body]")}
- Stronger-domain checker-adjudication `external_body` occurrences:
  {aggregate['checker_adjudication_literal_external_body_occurrences']}
- Whole-contract dependency proofs: 0
- No additional implementation/dependency boundary: 0
- Foundational end-to-end trust-free: 0
""",
        encoding="utf-8",
    )
    pipeline_path = ROOT / "research/PIPELINE_STATE.json"
    pipeline = json.loads(pipeline_path.read_text(encoding="utf-8"))
    pipeline["stages"]["implementation_completeness"] = {
        "status": "passed" if passed else "failed",
        "selected": total,
        "actual_verus_verified": summary[
            "implementation_actual_verus_verified"
        ],
        "actual_verus_native_verified": summary[
            "implementation_actual_verus_native_verified"
        ],
        "actual_verus_checker_adjudicated": summary[
            "implementation_actual_verus_checker_adjudicated"
        ],
        "completeness_verified": summary[
            "completeness_actual_verus_verified"
        ],
        "mutation_rejected": summary["mutations_rejected"],
        "mutation_native_rejected": summary["mutations_native_rejected"],
        "mutation_checker_adjudicated": summary[
            "mutations_checker_adjudicated"
        ],
        "pending": 0 if passed else total - summary["passed_targets"],
        "active_run_id": summary["run_id"],
    }
    atomic_json(pipeline_path, pipeline)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument(
        "--base-run-id",
        help=(
            "reuse passed, hash-identical logical trials from this immutable "
            "matrix and execute only changed sources"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory = json.loads(INVENTORY.read_text(encoding="utf-8"))
    rows = inventory["rows"]
    total_trials = 2 + len(rows) * 5
    base_summary: dict[str, Any] | None = None
    base_targets: dict[str, dict[str, Any]] = {}
    if args.base_run_id:
        if args.base_run_id == args.run_id:
            raise RuntimeError("base run and new run must be distinct")
        base_summary_path = (
            EVIDENCE_ROOT / args.base_run_id / "summary.json"
        )
        if not base_summary_path.is_file():
            raise RuntimeError(
                f"base matrix summary does not exist: {base_summary_path}"
            )
        base_summary = json.loads(
            base_summary_path.read_text(encoding="utf-8")
        )
        if (
            base_summary.get("status") != "passed"
            or base_summary.get("completed_targets") != len(rows)
        ):
            raise RuntimeError(
                f"base matrix is not reusable: {base_summary_path}"
            )
        base_targets = {
            item["target_id"]: item
            for item in base_summary.get("targets", [])
        }

    def target_trial_reusable(
        row: dict[str, Any],
        trial_name: str,
        source: Path,
    ) -> bool:
        if base_summary is None:
            return False
        target = base_targets.get(row["target_id"]) or {}
        trial = (target.get("trials") or {}).get(trial_name) or {}
        evidence = (
            ROOT
            / "proof_harnesses"
            / row["target_id"]
            / "evidence"
        )
        record_path = evidence / f"{trial_name}.json"
        if (
            trial.get("passed") is not True
            or trial.get("source_sha256") != sha256_file(source)
            or not record_path.is_file()
        ):
            return False
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if (
            record.get("passed") is not True
            or record.get("source_sha256") != sha256_file(source)
        ):
            return False
        if (
            row["target_id"]
            in proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
            and trial_name
            in {"implementation_actual_verus", "mutation_actual_verus"}
        ):
            fallback_source = (
                ROOT
                / "proof_harnesses"
                / row["target_id"]
                / (
                    "checker_adjudication_mutation.rs"
                    if trial_name == "mutation_actual_verus"
                    else "checker_adjudication_proof.rs"
                )
            )
            fallback = (
                evidence / f"{trial_name}_checker_adjudication.json"
            )
            if not fallback.is_file():
                return False
            fallback_record = json.loads(
                fallback.read_text(encoding="utf-8")
            )
            if (
                fallback_record.get("passed") is not True
                or fallback_record.get("source_sha256")
                != sha256_file(fallback_source)
            ):
                return False
        return True

    module_reuse: dict[str, bool] = {}
    for trial_name in (
        "generated_spec_no_verify",
        "generated_spec_actual_verus",
    ):
        record_path = (
            EVIDENCE_ROOT
            / str(args.base_run_id)
            / "module_evidence"
            / f"{trial_name}.json"
        )
        module_reuse[trial_name] = bool(
            base_summary is not None
            and record_path.is_file()
            and (
                lambda record: (
                    record.get("passed") is True
                    and record.get("source_sha256")
                    == sha256_file(
                        ROOT / "specs/generated_btree_set_specs.rs"
                    )
                )
            )(json.loads(record_path.read_text(encoding="utf-8")))
        )

    trial_sources = {
        "implementation_no_verify": "implementation_proof.rs",
        "implementation_actual_verus": "implementation_proof.rs",
        "completeness_no_verify": "completeness_proof.rs",
        "completeness_actual_verus": "completeness_proof.rs",
        "mutation_actual_verus": "mutation_proof.rs",
    }
    reused_logical_trials = sum(module_reuse.values())
    planned_verus_invocations = 2 - sum(module_reuse.values())
    for row in rows:
        target_root = ROOT / "proof_harnesses" / row["target_id"]
        associated = (
            row["target_id"]
            in proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
        )
        for trial_name, filename in trial_sources.items():
            reusable = target_trial_reusable(
                row,
                trial_name,
                target_root / filename,
            )
            if reusable:
                reused_logical_trials += 1
            else:
                planned_verus_invocations += (
                    2
                    if associated
                    and trial_name
                    in {
                        "implementation_actual_verus",
                        "mutation_actual_verus",
                    }
                    else 1
                )
    manifest = {
        "schema_version": 1,
        "run_id": args.run_id,
        "objective": (
            "Run generated-spec no-verify plus implementation/completeness "
            "no-verify, actual Verus, and a negative mutation for every "
            "selected API; narrowly adjudicate the three exact-signature "
            "IntoIterator::Item AIR failures with stronger-domain copies"
        ),
        "command": [
            sys.executable,
            "tools/run_verus_matrix.py",
            "--run-id",
            args.run_id,
            *(
                ["--base-run-id", args.base_run_id]
                if args.base_run_id
                else []
            ),
        ],
        "expected_trials": total_trials,
        "expected_verus_invocations": (
            total_trials
            + 2
            * len(proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS)
        ),
        "budget": {
            "per_trial_timeout_seconds": 90,
            "max_logical_trials": total_trials,
            "max_verus_invocations": (
                total_trials
                + 2
                * len(
                    proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
                )
            ),
        },
        "evidence_composition": {
            "base_run_id": args.base_run_id,
            "base_summary_sha256": (
                sha256_file(
                    EVIDENCE_ROOT
                    / str(args.base_run_id)
                    / "summary.json"
                )
                if args.base_run_id
                else None
            ),
            "reused_logical_trials": reused_logical_trials,
            "executed_logical_trials": (
                total_trials - reused_logical_trials
            ),
            "planned_verus_invocations": planned_verus_invocations,
            "policy": (
                "reuse only passed logical trials whose exact source hash "
                "still matches; execute every changed source in this run"
            ),
        },
        "source_snapshot": {
            "inventory": str(INVENTORY.relative_to(ROOT)),
            "inventory_sha256": sha256_file(INVENTORY),
            "verus": str(VERUS),
            "verus_sha256": sha256_file(VERUS),
            "z3": str(Z3),
            "z3_sha256": sha256_file(Z3),
            "accepted_specification_review": {
                "path": "reviews/inventory_specification.json",
                "sha256": sha256_file(
                    ROOT / "reviews/inventory_specification.json"
                ),
            },
            "generated_spec_sha256": sha256_file(
                ROOT / "specs/generated_btree_set_specs.rs"
            ),
            "shared_vocabulary_sha256": sha256_file(
                ROOT / "specs/btree_set_shared_vocabulary.rs"
            ),
        },
        "created_at": now(),
    }
    live = LiveRun(args.run_id, total_trials, manifest)
    live.status("running", "module_spec/generated_spec_no_verify")
    live.event("run_started", selected_targets=len(rows))
    versions = {
        "schema_version": 1,
        "captured_at": now(),
        "verus": subprocess.check_output([str(VERUS), "--version"], text=True).splitlines(),
        "z3": subprocess.check_output([str(Z3), "--version"], text=True).splitlines(),
    }
    atomic_json(live.root / "versions.json", versions)
    module_evidence = live.root / "module_evidence"
    if any(module_reuse.values()):
        copy_module_evidence(str(args.base_run_id), module_evidence)
    generated_spec = ROOT / "specs/generated_btree_set_specs.rs"
    spec_result = (
        reuse_trial(
            live,
            str(args.base_run_id),
            "module_spec",
            "generated_spec_no_verify",
            generated_spec,
            module_evidence,
        )
        if module_reuse["generated_spec_no_verify"]
        else execute_trial(
            live,
            "module_spec",
            "generated_spec_no_verify",
            generated_spec,
            no_verify=True,
            evidence_root=module_evidence,
        )
    )
    spec_actual_result = (
        reuse_trial(
            live,
            str(args.base_run_id),
            "module_spec",
            "generated_spec_actual_verus",
            generated_spec,
            module_evidence,
        )
        if module_reuse["generated_spec_actual_verus"]
        else execute_trial(
            live,
            "module_spec",
            "generated_spec_actual_verus",
            generated_spec,
            no_verify=False,
            evidence_root=module_evidence,
        )
    )

    def run_or_reuse(
        row: dict[str, Any],
        trial_name: str,
        source: Path,
        *,
        no_verify: bool,
        expected_mutation_failure: bool = False,
    ) -> dict[str, Any]:
        evidence = source.parent / "evidence"
        if target_trial_reusable(row, trial_name, source):
            return reuse_trial(
                live,
                str(args.base_run_id),
                row["target_id"],
                trial_name,
                source,
                evidence,
            )
        return execute_trial(
            live,
            row["target_id"],
            trial_name,
            source,
            no_verify=no_verify,
            expected_mutation_failure=expected_mutation_failure,
        )

    def run_or_reuse_adjudication(
        row: dict[str, Any],
        trial_name: str,
        exact_source: Path,
        adjudication_source: Path,
        *,
        expected_mutation_failure: bool,
    ) -> dict[str, Any]:
        if target_trial_reusable(row, trial_name, exact_source):
            return reuse_trial(
                live,
                str(args.base_run_id),
                row["target_id"],
                trial_name,
                exact_source,
                exact_source.parent / "evidence",
            )
        return execute_associated_item_adjudication(
            live,
            row["target_id"],
            trial_name,
            exact_source,
            adjudication_source,
            expected_mutation_failure=expected_mutation_failure,
        )

    target_summaries: list[dict[str, Any]] = []
    cancelled = False
    for row in rows:
        if live.cancelled():
            cancelled = True
            live.event("run_cancelled", target_id=row["target_id"])
            break
        target_root = ROOT / "proof_harnesses" / row["target_id"]
        evidence_root = target_root / "evidence"
        atomic_json(evidence_root / "versions.json", versions)
        records = [
            run_or_reuse(
                row,
                "implementation_no_verify",
                target_root / "implementation_proof.rs",
                no_verify=True,
            )
        ]
        if row["target_id"] in (
            proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
        ):
            records.append(
                run_or_reuse_adjudication(
                    row,
                    "implementation_actual_verus",
                    target_root / "implementation_proof.rs",
                    target_root / "checker_adjudication_proof.rs",
                    expected_mutation_failure=False,
                )
            )
        else:
            records.append(
                run_or_reuse(
                    row,
                    "implementation_actual_verus",
                    target_root / "implementation_proof.rs",
                    no_verify=False,
                )
            )
        records.extend(
            (
                run_or_reuse(
                    row,
                    "completeness_no_verify",
                    target_root / "completeness_proof.rs",
                    no_verify=True,
                ),
                run_or_reuse(
                    row,
                    "completeness_actual_verus",
                    target_root / "completeness_proof.rs",
                    no_verify=False,
                ),
            )
        )
        if row["target_id"] in (
            proof_model.ASSOCIATED_ITEM_AIR_ADJUDICATION_TARGETS
        ):
            records.append(
                run_or_reuse_adjudication(
                    row,
                    "mutation_actual_verus",
                    target_root / "mutation_proof.rs",
                    target_root / "checker_adjudication_mutation.rs",
                    expected_mutation_failure=True,
                )
            )
        else:
            records.append(
                run_or_reuse(
                    row,
                    "mutation_actual_verus",
                    target_root / "mutation_proof.rs",
                    no_verify=False,
                    expected_mutation_failure=True,
                )
            )
        target_passed = all(record["passed"] for record in records)
        target_summary = {
            "schema_version": 1,
            "target_id": row["target_id"],
            "contract_fingerprint": row["contract_fingerprint"],
            "passed": target_passed,
            "trials": {
                record["name"]: {
                    "passed": record["passed"],
                    "returncode": record["returncode"],
                    "source_sha256": record["source_sha256"],
                    "result_kind": record.get(
                        "result_kind",
                        "native_verus",
                    ),
                    "checker_limitation": record.get(
                        "checker_limitation"
                    ),
                    "reused_from_run_id": record.get(
                        "reused_from_run_id"
                    ),
                }
                for record in records
            },
        }
        atomic_json(evidence_root / "summary.json", target_summary)
        target_summaries.append(target_summary)
        live.status("running", row["target_id"])

    passed_targets = sum(item["passed"] for item in target_summaries)
    summary_relpath = f"verification/evidence/verus_matrix/{args.run_id}/summary.json"
    summary = {
        "schema_version": 1,
        "run_id": args.run_id,
        "status": (
            "cancelled"
            if cancelled
            else "passed"
            if spec_result["passed"]
            and spec_actual_result["passed"]
            and passed_targets == len(rows)
            and live.failed == 0
            else "failed"
        ),
        "expected_targets": len(rows),
        "completed_targets": len(target_summaries),
        "passed_targets": passed_targets,
        "failed_targets": len(target_summaries) - passed_targets,
        "generated_spec_no_verify": spec_result["passed"],
        "generated_spec_actual_verus": spec_actual_result["passed"],
        "implementation_no_verify_passed": sum(
            item["trials"]["implementation_no_verify"]["passed"]
            for item in target_summaries
        ),
        "implementation_actual_verus_verified": sum(
            item["trials"]["implementation_actual_verus"]["passed"]
            for item in target_summaries
        ),
        "implementation_actual_verus_native_verified": sum(
            item["trials"]["implementation_actual_verus"]["passed"]
            and item["trials"]["implementation_actual_verus"][
                "result_kind"
            ]
            == "native_verus"
            for item in target_summaries
        ),
        "implementation_actual_verus_checker_adjudicated": sum(
            item["trials"]["implementation_actual_verus"]["passed"]
            and item["trials"]["implementation_actual_verus"][
                "result_kind"
            ]
            == "checker_adjudicated"
            for item in target_summaries
        ),
        "completeness_no_verify_passed": sum(
            item["trials"]["completeness_no_verify"]["passed"]
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
        "mutations_native_rejected": sum(
            item["trials"]["mutation_actual_verus"]["passed"]
            and item["trials"]["mutation_actual_verus"]["result_kind"]
            == "native_verus"
            for item in target_summaries
        ),
        "mutations_checker_adjudicated": sum(
            item["trials"]["mutation_actual_verus"]["passed"]
            and item["trials"]["mutation_actual_verus"]["result_kind"]
            == "checker_adjudicated"
            for item in target_summaries
        ),
        "trial_failures": live.failed,
        "base_run_id": args.base_run_id,
        "reused_logical_trials": reused_logical_trials,
        "executed_logical_trials": (
            total_trials - reused_logical_trials
        ),
        "planned_verus_invocations": planned_verus_invocations,
        "summary_path": summary_relpath,
        "completed_at": now(),
        "targets": target_summaries,
    }
    atomic_json(live.root / "summary.json", summary)
    live.status(summary["status"], None)
    live.event("run_completed", status=summary["status"], passed_targets=passed_targets)
    if not cancelled:
        update_campaign(rows, summary)
    print(json.dumps({key: summary[key] for key in (
        "run_id",
        "status",
        "expected_targets",
        "passed_targets",
        "trial_failures",
    )}, sort_keys=True))
    return 0 if summary["status"] == "passed" else 130 if cancelled else 1


if __name__ == "__main__":
    raise SystemExit(main())
